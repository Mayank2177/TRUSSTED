"""Policy input/output value types. These carry evidence; they do not infer it."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType


class ConflictSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DecisionResult(StrEnum):
    ALLOW = "ALLOW"
    STEP_UP = "STEP_UP"
    BLOCK = "BLOCK"


class ReasonCode(StrEnum):
    HIGH_SEVERITY_CONFLICT = "HIGH_SEVERITY_CONFLICT"
    WINNER_NOT_PERMITTED = "WINNER_NOT_PERMITTED"
    HARD_CONSTRAINT_VIOLATION = "HARD_CONSTRAINT_VIOLATION"
    WINNER_UNSTABLE = "WINNER_UNSTABLE"
    NO_REFERENCE_OVER_THRESHOLD = "NO_REFERENCE_OVER_THRESHOLD"
    UPSTREAM_FAILURE = "UPSTREAM_FAILURE"
    REQUIRED_EVIDENCE_MISSING = "REQUIRED_EVIDENCE_MISSING"
    INVALID_POLICY_INPUT = "INVALID_POLICY_INPUT"
    STEP_UP_THRESHOLD_NOT_CONFIGURED = "STEP_UP_THRESHOLD_NOT_CONFIGURED"
    CHECKS_PASSED = "CHECKS_PASSED"


@dataclass(frozen=True, slots=True)
class FactConflict:
    field: str
    severity: ConflictSeverity
    fact_id: str | None = None


@dataclass(frozen=True, slots=True)
class UpstreamFailure:
    stage: str
    code: str


@dataclass(frozen=True, slots=True)
class PolicyInput:
    run_id: str
    winner_candidate_id: str | None
    winner_permitted: bool | None
    hard_constraints_satisfied: bool | None
    stability_stable: bool | None
    no_reference: bool | None
    amount_minor: int | None
    currency: str | None
    conflicts: tuple[FactConflict, ...] = ()
    upstream_failures: tuple[UpstreamFailure, ...] = ()
    winner_fact_id: str | None = None


@dataclass(frozen=True, slots=True)
class PolicyConfig:
    policy_version: str
    no_reference_step_up_thresholds_minor: Mapping[str, int]

    def __post_init__(self) -> None:
        if not isinstance(self.policy_version, str) or not self.policy_version.strip():
            raise ValueError("policy_version must be non-empty")
        if not isinstance(self.no_reference_step_up_thresholds_minor, Mapping):
            raise ValueError("threshold configuration must be a mapping")
        thresholds = dict(self.no_reference_step_up_thresholds_minor)
        for currency, amount in thresholds.items():
            if not isinstance(currency, str) or re.fullmatch(r"[A-Z]{3}", currency) is None:
                raise ValueError(f"invalid currency code in policy configuration: {currency!r}")
            if type(amount) is not int or amount < 0:
                raise ValueError("thresholds must be non-negative integer minor units")
        object.__setattr__(
            self, "no_reference_step_up_thresholds_minor", MappingProxyType(thresholds)
        )

    @property
    def effective_policy_version(self) -> str:
        """Identify both the policy family and its actual currency threshold settings."""
        canonical = json.dumps(
            {
                "policy_version": self.policy_version,
                "no_reference_step_up_thresholds_minor": dict(
                    self.no_reference_step_up_thresholds_minor
                ),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        fingerprint = hashlib.sha256(canonical).hexdigest()[:16]
        return f"{self.policy_version}+{fingerprint}"


@dataclass(frozen=True, slots=True)
class Decision:
    run_id: str
    result: DecisionResult
    reasons: tuple[ReasonCode, ...]
    policy_version: str
    amount_minor: int | None
    currency: str | None
    winner_fact_id: str | None = None
    approval_hash: str | None = None
