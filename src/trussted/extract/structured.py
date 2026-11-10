"""Parse schema.org Product data from JSON-LD blocks. The result is untrusted page data."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from ..errors import ValidationError
from ..models.facts import StructuredProduct
from ..models.ids import normalize_gtin
from ..models.money import parse_amount

_GTIN_KEYS = ("gtin", "gtin8", "gtin12", "gtin13", "gtin14")
_MAX_NODES = 2_000
_MAX_SPECS = 100


def _str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def _type_names(node: dict[str, Any]) -> set[str]:
    raw = node.get("@type")
    items = raw if isinstance(raw, list) else [raw]
    return {t.rsplit("/", 1)[-1] for t in items if isinstance(t, str)}


def _price(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        d = Decimal(str(value))
        return d if d.is_finite() and d >= 0 else None
    if isinstance(value, str):
        try:
            return parse_amount(value)
        except ValidationError:
            return None
    return None


def _offer(node: dict[str, Any]) -> tuple[Decimal | None, str | None]:
    offers = node.get("offers")
    items = offers if isinstance(offers, list) else [offers]
    found: list[tuple[Decimal, str | None]] = []
    for o in items:
        if not isinstance(o, dict):
            continue
        price = _price(o.get("price", o.get("lowPrice")))
        if price is not None:
            cur = o.get("priceCurrency")
            found.append((price, cur.upper() if isinstance(cur, str) else None))
    distinct = set(found)
    if len(distinct) == 1:
        return next(iter(distinct))
    return None, None  # none, or ambiguous multiple offers


def _walk(data: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    stack = [data]
    while stack and len(out) < _MAX_NODES:
        cur = stack.pop()
        if isinstance(cur, list):
            stack.extend(cur)
        elif isinstance(cur, dict):
            out.append(cur)
            graph = cur.get("@graph")
            if isinstance(graph, list):
                stack.extend(graph)
    return out


def parse_jsonld_products(blocks: list[str]) -> tuple[list[StructuredProduct], list[str]]:
    products: list[StructuredProduct] = []
    flags: list[str] = []
    for raw in blocks:
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, RecursionError):
            flags.append("invalid_jsonld")
            continue
        for node in _walk(data):
            if "Product" not in _type_names(node):
                continue
            brand = node.get("brand")
            brand_name = _str(brand.get("name")) if isinstance(brand, dict) else _str(brand)
            gtin = next(
                (g for k in _GTIN_KEYS if (g := normalize_gtin(_str(node.get(k)) or ""))), None
            )
            specs: dict[str, str] = {}
            props = node.get("additionalProperty")
            for p in (props if isinstance(props, list) else []):
                if isinstance(p, dict) and len(specs) < _MAX_SPECS:
                    k, v = _str(p.get("name")), _str(p.get("value"))
                    if k and v:
                        specs[k] = v
            price, currency = _offer(node)
            products.append(StructuredProduct(
                name=_str(node.get("name")), brand=brand_name, sku=_str(node.get("sku")),
                gtin=gtin, price=price, currency=currency, specs=specs,
            ))
    return products, flags
