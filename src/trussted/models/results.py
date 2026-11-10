"""Stage outputs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from .facts import FactVerification, Observation, ProductFact, RejectedFact
from .money import Money


class ViolationCode(StrEnum):
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    OVER_BUDGET = "OVER_BUDGET"
    BRAND_NOT_ALLOWED = "BRAND_NOT_ALLOWED"
    BRAND_BLOCKED = "BRAND_BLOCKED"
    BRAND_UNKNOWN = "BRAND_UNKNOWN"
    MERCHANT_NOT_ALLOWED = "MERCHANT_NOT_ALLOWED"
    MERCHANT_BLOCKED = "MERCHANT_BLOCKED"
    SPEC_MISSING = "SPEC_MISSING"
    SPEC_MISMATCH = "SPEC_MISMATCH"
    SPEC_UNCOMPARABLE = "SPEC_UNCOMPARABLE"
    RECURRING_CHARGE = "RECURRING_CHARGE"
    RECURRING_UNKNOWN = "RECURRING_UNKNOWN"
    DELIVERY_TOO_SLOW = "DELIVERY_TOO_SLOW"
    DELIVERY_UNKNOWN = "DELIVERY_UNKNOWN"
    CONDITION_NOT_ALLOWED = "CONDITION_NOT_ALLOWED"
    CONDITION_UNKNOWN = "CONDITION_UNKNOWN"
    SHIPPING_UNKNOWN = "SHIPPING_UNKNOWN"
    FACT_CONFLICT_HIGH = "FACT_CONFLICT_HIGH"


class FlagCode(StrEnum):
    COST_LOWER_BOUND = "COST_LOWER_BOUND"  # shipping/charges unknown; total may be higher
    NO_INDEPENDENT_REFERENCE = "NO_INDEPENDENT_REFERENCE"
    CONFLICT_PRESENT = "CONFLICT_PRESENT"
    RECURRING_UNKNOWN = "RECURRING_UNKNOWN"
    DELIVERY_UNKNOWN = "DELIVERY_UNKNOWN"
    CONDITION_UNKNOWN = "CONDITION_UNKNOWN"
    EXTRACTION_WARNINGS = "EXTRACTION_WARNINGS"


@dataclass(frozen=True, slots=True)
class Violation:
    code: ViolationCode
    detail: str


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    rank: int
    fact: ProductFact
    total_cost: Money
    score: Decimal
    flags: tuple[FlagCode, ...] = ()


@dataclass(frozen=True, slots=True)
class DisqualifiedCandidate:
    fact: ProductFact
    violations: tuple[Violation, ...]


@dataclass(frozen=True, slots=True)
class RankResult:
    ranked: tuple[RankedCandidate, ...]
    disqualified: tuple[DisqualifiedCandidate, ...]
    winner_fact_id: str | None
    winner_margin: Decimal | None  # score gap between 1st and 2nd; None if < 2 ranked


@dataclass(frozen=True, slots=True)
class StageError:
    stage: str
    ref: str
    message: str


@dataclass(frozen=True, slots=True)
class SelectionResult:
    observations: tuple[Observation, ...]
    facts: tuple[ProductFact, ...]
    rejected: tuple[RejectedFact, ...]
    verifications: tuple[FactVerification, ...]
    ranking: RankResult
    stage_errors: tuple[StageError, ...]
    warnings: tuple[str, ...] = ()

    @property
    def has_errors(self) -> bool:
        return bool(self.stage_errors)

    @property
    def winner_candidate(self) -> RankedCandidate | None:
        wid = self.ranking.winner_fact_id
        return next((c for c in self.ranking.ranked if c.fact.fact_id == wid), None) if wid else None

    @property
    def winner(self) -> ProductFact | None:
        wid = self.ranking.winner_fact_id
        return next((f for f in self.facts if f.fact_id == wid), None) if wid else None
