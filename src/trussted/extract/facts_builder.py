"""Validate one LLM product record and ground it in the page text. Fail closed per record."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from ..config import ExtractionConfig
from ..errors import ValidationError
from ..models.facts import ProductFact
from ..models.ids import normalize_gtin
from ..models.money import Money, parse_amount
from .schema import CONDITIONS


class Rejected(Exception):
    """Raised to discard a single product record with a machine-readable reason."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def normalize_for_match(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _price_in_evidence(price_text: str, evidence: str) -> bool:
    """True if the numeric price appears in the evidence as a standalone number."""
    candidates = {price_text}
    if "." in price_text:
        stripped = price_text.rstrip("0").rstrip(".")
        if stripped:
            candidates.add(stripped)
    haystack = evidence.replace(",", "")
    return any(
        re.search(rf"(?<![\d.]){re.escape(c)}(?!\d|\.\d)", haystack) for c in candidates
    )


def _opt_text(value: Any, cap: int) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()[:cap]
    return None


def _opt_int(value: Any, lo: int, hi: int) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int) and lo <= value <= hi:
        return value
    return None


def build_fact(
    *, index: int, raw: Any, observation_id: str, merchant_id: str,
    normalized_page_text: str, cfg: ExtractionConfig, source_url: str | None = None,
) -> ProductFact:
    if not isinstance(raw, Mapping):
        raise Rejected("not_an_object")
    warnings: list[str] = []

    name = _opt_text(raw.get("name"), cfg.max_text_field_chars)
    if not name:
        raise Rejected("missing_name")

    price_text = raw.get("price")
    currency = raw.get("currency")
    if not isinstance(price_text, str) or not isinstance(currency, str):
        raise Rejected("invalid_price")
    currency = currency.strip().upper()
    try:
        price_dec = parse_amount(price_text)
        price = Money.from_decimal(price_dec, currency)
    except ValidationError as exc:
        raise Rejected(f"invalid_price:{exc}") from exc
    if price.amount_minor <= 0:
        raise Rejected("non_positive_price")

    evidence = raw.get("evidence")
    if not isinstance(evidence, str) or len(evidence.strip()) < cfg.min_evidence_chars:
        raise Rejected("evidence_missing")
    if normalize_for_match(evidence) not in normalized_page_text:
        raise Rejected("evidence_not_in_page")
    if not _price_in_evidence(price_text.strip().replace(",", ""), evidence):
        raise Rejected("price_not_in_evidence")

    def money_field(key: str) -> Money | None:
        value = raw.get(key)
        if value is None:
            return None
        try:
            if not isinstance(value, str):
                raise ValidationError("not a string")
            return Money.from_decimal(parse_amount(value), currency)
        except ValidationError:
            warnings.append(f"invalid_{key}")
            return None

    rating: Decimal | None = None
    if raw.get("rating") is not None:
        try:
            candidate = parse_amount(str(raw["rating"]))
            if candidate <= Decimal("5"):
                rating = candidate
            else:
                warnings.append("invalid_rating")
        except ValidationError:
            warnings.append("invalid_rating")

    gtin = None
    if raw.get("gtin") is not None:
        gtin = normalize_gtin(str(raw["gtin"]))
        if gtin is None:
            warnings.append("invalid_gtin")

    recurring = raw.get("is_recurring")
    if recurring is not None and not isinstance(recurring, bool):
        warnings.append("invalid_is_recurring")
        recurring = None

    cond = raw.get("condition")
    condition = cond.strip().lower() if isinstance(cond, str) else "unknown"
    if condition not in CONDITIONS:
        warnings.append("invalid_condition")
        condition = "unknown"

    specs: dict[str, str] = {}
    raw_specs = raw.get("specs")
    if isinstance(raw_specs, Mapping):
        seen: set[str] = set()
        for k, v in raw_specs.items():
            key = _opt_text(k, cfg.max_text_field_chars)
            val = _opt_text(v if isinstance(v, str) else str(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None, cfg.max_text_field_chars)
            if not key or not val:
                continue
            folded = key.casefold()
            if folded in seen:
                warnings.append(f"duplicate_spec:{folded}")
                continue
            if len(specs) >= cfg.max_specs_per_product:
                warnings.append("specs_truncated")
                break
            seen.add(folded)
            specs[key] = val
    elif raw_specs is not None:
        warnings.append("invalid_specs")

    return ProductFact(
        fact_id=f"{observation_id}:{index}",
        observation_id=observation_id,
        merchant_id=merchant_id,
        name=name,
        price=price,
        evidence=evidence.strip(),
        brand=_opt_text(raw.get("brand"), cfg.max_text_field_chars),
        sku=_opt_text(raw.get("sku"), cfg.max_text_field_chars),
        gtin=gtin,
        shipping=money_field("shipping_price"),
        additional_charges=money_field("additional_charges"),
        is_recurring=recurring,
        delivery_days=_opt_int(raw.get("delivery_days"), 0, 365),
        rating=rating,
        review_count=_opt_int(raw.get("review_count"), 0, 10**9),
        condition=condition,  # type: ignore[arg-type]
        specs=specs,
        warnings=tuple(warnings),
        source_url=source_url,
    )
