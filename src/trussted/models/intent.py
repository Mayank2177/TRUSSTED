"""The user's purchase instruction, as a validated, immutable object."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from ..errors import ValidationError
from .money import Money, currency_exponent
from .units import SpecOp, parse_spec_value

_OPS = ("eq", "gte", "lte", "in")


@dataclass(frozen=True, slots=True)
class SpecConstraint:
    key: str
    op: SpecOp
    values: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValidationError("spec constraint key is empty")
        if self.op not in _OPS:
            raise ValidationError(f"unknown op {self.op!r}")
        if not self.values:
            raise ValidationError("spec constraint needs at least one value")
        if self.op != "in" and len(self.values) != 1:
            raise ValidationError(f"op {self.op!r} takes exactly one value")
        for v in self.values:
            parse_spec_value(v)  # validates


@dataclass(frozen=True, slots=True)
class ScoringWeights:
    price: Decimal = Decimal("1")
    delivery: Decimal = Decimal("0")
    rating: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        for name in ("price", "delivery", "rating"):
            v = getattr(self, name)
            if not isinstance(v, Decimal) or not v.is_finite() or v < 0:
                raise ValidationError(f"weight {name} must be a finite Decimal >= 0")
        if self.price + self.delivery + self.rating <= 0:
            raise ValidationError("at least one weight must be positive")


def _lower_set(values: frozenset[str] | set[str] | tuple[str, ...]) -> frozenset[str]:
    return frozenset(v.strip().casefold() for v in values if v.strip())


@dataclass(frozen=True, slots=True)
class UserIntent:
    """What the user asked for. Hard constraints eliminate; weights only rank survivors."""

    description: str
    currency: str
    quantity: int = 1
    max_total: Money | None = None
    spec_constraints: tuple[SpecConstraint, ...] = ()
    allowed_brands: frozenset[str] = frozenset()
    blocked_brands: frozenset[str] = frozenset()
    allowed_merchants: frozenset[str] = frozenset()
    blocked_merchants: frozenset[str] = frozenset()
    allow_recurring: bool = False
    allow_used: bool = False
    max_delivery_days: int | None = None
    weights: ScoringWeights = field(default_factory=ScoringWeights)

    def __post_init__(self) -> None:
        if not self.description.strip():
            raise ValidationError("description is empty")
        currency_exponent(self.currency)
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int) or self.quantity < 1:
            raise ValidationError("quantity must be an int >= 1")
        if self.max_total is not None:
            if self.max_total.currency != self.currency:
                raise ValidationError("max_total currency must equal intent currency")
            if self.max_total.amount_minor <= 0:
                raise ValidationError("max_total must be positive")
        if self.max_delivery_days is not None and self.max_delivery_days < 0:
            raise ValidationError("max_delivery_days must be >= 0")
        for name in ("allowed_brands", "blocked_brands", "allowed_merchants", "blocked_merchants"):
            object.__setattr__(self, name, _lower_set(getattr(self, name)))
        if self.allowed_brands & self.blocked_brands:
            raise ValidationError("a brand is both allowed and blocked")
        if self.allowed_merchants & self.blocked_merchants:
            raise ValidationError("a merchant is both allowed and blocked")
