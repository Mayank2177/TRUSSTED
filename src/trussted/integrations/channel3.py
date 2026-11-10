"""Channel3 product API: discovery and an independent price/brand reference.

Docs: POST {base}/v1/search and POST {base}/v1/lookup with an ``x-api-key`` header. The public
docs show several response shapes for offers (price as object or number; ``domain`` vs
``merchant_domain``), so parsing is deliberately tolerant and drops anything it cannot validate.
Prices are treated as major units (e.g. 110 USD). VERIFY against a live key before relying on it.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any

from ..config import Channel3Config
from ..errors import ConfigError, IntegrationError, ValidationError
from ..models.facts import CandidateSet, Observation, ProductFact
from ..models.money import Money
from ..verify.reference import ReferenceRecord
from .http import HttpTransport, UrllibTransport, send_json

_CURRENCY = re.compile(r"^[A-Z]{3}$")
_IN_STOCK = frozenset({"instock", "in_stock", "in stock", "available"})


@dataclass(frozen=True, slots=True)
class Channel3Offer:
    domain: str
    price: Decimal
    currency: str
    availability: str | None
    url: str | None


@dataclass(frozen=True, slots=True)
class Channel3Product:
    id: str
    title: str
    brand: str | None
    offers: tuple[Channel3Offer, ...]
    attributes: Mapping[str, str]


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        d = Decimal(str(value).strip())
    except InvalidOperation:
        return None
    return d if d.is_finite() and d > 0 else None


def _parse_offer(raw: Any) -> Channel3Offer | None:
    if not isinstance(raw, Mapping):
        return None
    domain = raw.get("domain") or raw.get("merchant_domain")
    price_raw, currency = raw.get("price"), raw.get("currency")
    if isinstance(price_raw, Mapping):
        currency = price_raw.get("currency", currency)
        price_raw = price_raw.get("amount", price_raw.get("price"))
    price = _decimal(price_raw)
    if not isinstance(domain, str) or not domain.strip() or price is None:
        return None
    if not isinstance(currency, str) or not _CURRENCY.match(currency.strip().upper()):
        return None
    avail = raw.get("availability")
    if isinstance(avail, Mapping):
        avail = "InStock" if avail.get("available") is True else "OutOfStock"
    url = raw.get("url")
    return Channel3Offer(
        domain=domain.strip().casefold().removeprefix("www."), price=price,
        currency=currency.strip().upper(),
        availability=avail if isinstance(avail, str) else None,
        url=url if isinstance(url, str) else None,
    )


def parse_product(raw: Any) -> Channel3Product | None:
    if not isinstance(raw, Mapping):
        return None
    pid, title = raw.get("id"), raw.get("title")
    if not isinstance(pid, str) or not pid or not isinstance(title, str) or not title.strip():
        return None
    brand_raw = raw.get("brand")
    if brand_raw is None and isinstance(raw.get("brands"), list) and raw["brands"]:
        brand_raw = raw["brands"][0]
    brand = brand_raw.get("name") if isinstance(brand_raw, Mapping) else brand_raw
    offers_raw = raw.get("offers")
    offers = tuple(o for o in (_parse_offer(x) for x in (offers_raw if isinstance(offers_raw, list) else [])) if o)
    attrs_raw = raw.get("structured_attributes")
    attrs = {str(k): str(v) for k, v in attrs_raw.items()
             if isinstance(attrs_raw, Mapping) and isinstance(v, (str, int, float)) and not isinstance(v, bool)} \
        if isinstance(attrs_raw, Mapping) else {}
    return Channel3Product(pid, title.strip(), brand.strip() if isinstance(brand, str) and brand.strip() else None,
                           offers, MappingProxyType(attrs))


class Channel3Client:
    def __init__(
        self, config: Channel3Config, *, api_key: str | None = None,
        transport: HttpTransport | None = None, sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        key = api_key or os.environ.get(config.api_key_env, "")
        if not key:
            raise ConfigError(f"Channel3 API key missing: set {config.api_key_env}")
        self._cfg, self._key = config, key
        self._transport = transport or UrllibTransport()
        self._sleep = sleep

    def _post(self, path: str, payload: Mapping[str, Any]) -> tuple[int, Any]:
        status, data = send_json(
            self._transport, "POST", f"{self._cfg.base_url}{path}",
            headers={"x-api-key": self._key, "Content-Type": "application/json",
                     "Accept": "application/json"},
            payload=payload, timeout_s=self._cfg.timeout_s, retries=self._cfg.max_retries,
            backoff_s=self._cfg.retry_backoff_s, sleep=self._sleep,
        )
        if status in (401, 403):
            raise IntegrationError("Channel3 rejected the API key")
        if status == 402:
            raise IntegrationError("Channel3 payment required (quota exhausted)")
        return status, data

    def search(self, query: str, *, limit: int | None = None) -> list[Channel3Product]:
        if not query.strip():
            raise ValidationError("query is empty")
        n = limit if limit is not None else self._cfg.default_limit
        if not 1 <= n <= self._cfg.max_limit:
            raise ValidationError(f"limit must be in [1, {self._cfg.max_limit}]")
        status, data = self._post("/v1/search", {"query": query.strip(), "limit": n})
        if not 200 <= status < 300 or not isinstance(data, Mapping) \
                or not isinstance(data.get("products"), list):
            raise IntegrationError(f"Channel3 search failed (HTTP {status})")
        return [p for p in (parse_product(x) for x in data["products"]) if p is not None]

    def lookup(self, url: str) -> Channel3Product | None:
        status, data = self._post("/v1/lookup", {"url": url})
        if status == 404:
            return None
        if not 200 <= status < 300:
            raise IntegrationError(f"Channel3 lookup failed (HTTP {status})")
        body = data.get("product", data) if isinstance(data, Mapping) else None
        return parse_product(body)


class Channel3Reference:
    """Independent reference: what does Channel3 say this page's merchant charges?

    Uses the fact's page URL, so it is independent of the page text. Do NOT use it on facts
    that were themselves built from Channel3 results (those carry no ``source_url``).
    """

    name = "channel3"

    def __init__(self, client: Channel3Client, *, cache_size: int = 256) -> None:
        self._client = client
        self._cache: OrderedDict[str, Channel3Product | None] = OrderedDict()
        self._size = cache_size
        self._lock = threading.Lock()

    def _product(self, url: str) -> Channel3Product | None:
        with self._lock:
            if url in self._cache:
                self._cache.move_to_end(url)
                return self._cache[url]
        product = self._client.lookup(url)
        with self._lock:
            self._cache[url] = product
            while len(self._cache) > self._size:
                self._cache.popitem(last=False)
        return product

    def lookup(self, fact: ProductFact) -> ReferenceRecord | None:
        if not fact.source_url:
            return None
        product = self._product(fact.source_url)
        if product is None:
            return None
        domain = fact.merchant_id.casefold()
        offers = [o for o in product.offers if domain == o.domain or domain.endswith("." + o.domain)
                  or o.domain.endswith("." + domain)]
        if not offers or len({(o.price, o.currency) for o in offers}) != 1:
            return None  # no offer from this merchant, or ambiguous
        offer = offers[0]
        return ReferenceRecord(
            merchant_id=offer.domain, sku=product.id, brand=product.brand,
            price=Money.from_decimal(offer.price, offer.currency),
        )


def candidates_from_search(query: str, products: Sequence[Channel3Product]) -> CandidateSet:
    """Turn in-stock offers into pre-structured candidates. They have NO independent reference
    (Channel3 is their only source), so policy will step up on higher-value purchases."""
    digest = hashlib.sha256(json.dumps(
        [(p.id, [(o.domain, str(o.price), o.currency) for o in p.offers]) for p in products],
        sort_keys=True).encode()).hexdigest()
    obs_id = f"ch3_{digest[:16]}"
    facts: list[ProductFact] = []
    for p in products:
        for i, o in enumerate(p.offers):
            if (o.availability or "").strip().casefold() not in _IN_STOCK:
                continue
            try:
                price = Money.from_decimal(o.price, o.currency)
            except ValidationError:
                continue
            facts.append(ProductFact(
                fact_id=f"{obs_id}:{p.id}:{i}", observation_id=obs_id, merchant_id=o.domain,
                name=p.title, price=price, evidence=f"channel3:{p.id}:{o.domain}", brand=p.brand,
                sku=p.id, specs=dict(p.attributes),
            ))
    obs = Observation(
        observation_id=obs_id, url=f"channel3:search:{hashlib.sha256(query.encode()).hexdigest()[:12]}",
        merchant_id="api.trychannel3.com", content_hash=digest, text_chars=0,
        hidden_chars_removed=0, control_chars_removed=0, truncated=False, flags=(),
    )
    return CandidateSet((obs,), tuple(facts))
