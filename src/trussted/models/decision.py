"""Policy output."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .money import Money


class DecisionResult(StrEnum):
    ALLOW = "ALLOW"        # proceed to payment (PayPal still requires the buyer's own approval)
    STEP_UP = "STEP_UP"    # a human must review before any payment is created
    BLOCK = "BLOCK"        # do not pay


class ReasonCode(StrEnum):
    NO_ELIGIBLE_CANDIDATE = "NO_ELIGIBLE_CANDIDATE"
    STAGE_ERROR = "STAGE_ERROR"
    RECHECK_CURRENCY = "RECHECK_CURRENCY"
    RECHECK_BUDGET = "RECHECK_BUDGET"
    RECHECK_TOTAL = "RECHECK_TOTAL"
    FACT_CONFLICT = "FACT_CONFLICT"
    NO_INDEPENDENT_REFERENCE = "NO_INDEPENDENT_REFERENCE"
    RISK_FLAG = "RISK_FLAG"
    PAGE_FLAG = "PAGE_FLAG"
    CLOSE_CALL = "CLOSE_CALL"
    HIGH_VALUE = "HIGH_VALUE"
    CLEAN = "CLEAN"


@dataclass(frozen=True, slots=True)
class Reason:
    code: ReasonCode
    detail: str
    result: DecisionResult  # the outcome this reason alone would require


@dataclass(frozen=True, slots=True)
class Decision:
    result: DecisionResult
    reasons: tuple[Reason, ...]
    winner_fact_id: str | None
    amount: Money | None
    policy_version: str
