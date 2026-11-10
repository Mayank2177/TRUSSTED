"""Observation and fact models produced by extraction and verification."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Literal

from ..config import Severity
from ..errors import ValidationError
from .money import Money

Condition = Literal["new", "used", "refurbished", "unknown"]
VerificationStatus = Literal["verified", "conflict", "no_reference"]
_CONDITIONS = ("new", "used", "refurbished", "unknown")


@dataclass(frozen=True, slots=True)
class PageInput:
    url: str
    html: str


@dataclass(frozen=True, slots=True)
class StructuredProduct:
    """A product declared in the page's own structured data (e.g. JSON-LD). Untrusted."""

    name: str | None
    brand: str | None
    sku: str | None
    gtin: str | None
    price: Decimal | None
    currency: str | None
    specs: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class Observation:
    observation_id: str
    url: str
    merchant_id: str
    content_hash: str
    text_chars: int
    hidden_chars_removed: int
    control_chars_removed: int
    truncated: bool
    flags: tuple[str, ...]
    structured: tuple[StructuredProduct, ...] = ()


@dataclass(frozen=True, slots=True)
class ProductFact:
    fact_id: str
    observation_id: str
    merchant_id: str
    name: str
    price: Money
    evidence: str
    brand: str | None = None
    sku: str | None = None
    gtin: str | None = None
    shipping: Money | None = None
    additional_charges: Money | None = None
    is_recurring: bool | None = None
    delivery_days: int | None = None
    rating: Decimal | None = None
    review_count: int | None = None
    condition: Condition = "unknown"
    specs: Mapping[str, str] = MappingProxyType({})
    warnings: tuple[str, ...] = ()
    source_url: str | None = None

    def __post_init__(self) -> None:
        if not self.fact_id or not self.name.strip():
            raise ValidationError("fact requires id and name")
        if self.price.amount_minor <= 0:
            raise ValidationError("price must be positive")
        if self.condition not in _CONDITIONS:
            raise ValidationError(f"invalid condition {self.condition!r}")
        object.__setattr__(self, "specs", MappingProxyType(dict(self.specs)))


@dataclass(frozen=True, slots=True)
class RejectedFact:
    observation_id: str
    index: int
    reason: str
    name: str | None = None


@dataclass(frozen=True, slots=True)
class FactConflict:
    fact_id: str
    kind: str  # price | currency | brand | spec | recurring
    field: str
    extracted: str
    reference: str
    severity: Severity
    source: str


@dataclass(frozen=True, slots=True)
class FactVerification:
    fact_id: str
    status: VerificationStatus
    conflicts: tuple[FactConflict, ...] = ()
    sources: tuple[str, ...] = ()
    independent_sources: tuple[str, ...] = ()

    @property
    def has_high_conflict(self) -> bool:
        return any(c.severity == "high" for c in self.conflicts)


@dataclass(frozen=True, slots=True)
class CandidateSet:
    """Pre-structured candidates (e.g. from a product API) to rank alongside extracted pages."""

    observations: tuple[Observation, ...]
    facts: tuple[ProductFact, ...]
