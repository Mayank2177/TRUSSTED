"""Pure, priority-ordered implementation of the PRD's Stage 5 decision table."""

from __future__ import annotations

import hashlib
import json
import re

from warrant.policy.models import (
    ConflictSeverity,
    Decision,
    DecisionResult,
    FactConflict,
    PolicyConfig,
    PolicyInput,
    ReasonCode,
    UpstreamFailure,
)


def decide(inputs: PolicyInput, config: PolicyConfig) -> Decision:
    """Evaluate evidence deterministically; missing or invalid evidence cannot ALLOW."""
    if not isinstance(inputs, PolicyInput) or not isinstance(config, PolicyConfig):
        return Decision(
            run_id=(inputs.run_id if isinstance(inputs, PolicyInput) else "invalid-run"),
            result=DecisionResult.STEP_UP,
            reasons=(ReasonCode.INVALID_POLICY_INPUT,),
            policy_version=(
                config.effective_policy_version
                if isinstance(config, PolicyConfig)
                else "invalid-policy-config"
            ),
            amount_minor=None,
            currency=None,
        )
    reasons: list[ReasonCode] = []

    # Priority 1: any high-severity conflict blocks regardless of other evidence.
    if isinstance(inputs.conflicts, tuple) and any(
        isinstance(conflict, FactConflict) and conflict.severity is ConflictSeverity.HIGH
        for conflict in inputs.conflicts
    ):
        reasons.append(ReasonCode.HIGH_SEVERITY_CONFLICT)

    # Priority 2: hard user constraints and merchant permission are hard blockers.
    if inputs.winner_permitted is False:
        reasons.append(ReasonCode.WINNER_NOT_PERMITTED)
    if inputs.hard_constraints_satisfied is False:
        reasons.append(ReasonCode.HARD_CONSTRAINT_VIOLATION)

    invalid = _input_error(inputs)
    if invalid is not None:
        reasons.append(invalid)
    if inputs.winner_candidate_id is None or inputs.winner_permitted is None:
        reasons.append(ReasonCode.REQUIRED_EVIDENCE_MISSING)
    if inputs.hard_constraints_satisfied is None or inputs.stability_stable is None:
        reasons.append(ReasonCode.REQUIRED_EVIDENCE_MISSING)
    if inputs.no_reference is None:
        reasons.append(ReasonCode.REQUIRED_EVIDENCE_MISSING)

    # Priority 3: an unstable winner requires a human step-up.
    if inputs.stability_stable is False:
        reasons.append(ReasonCode.WINNER_UNSTABLE)

    # Priority 4: no independent reference at or above the configured threshold.
    if (
        inputs.no_reference is True
        and type(inputs.amount_minor) is int
        and inputs.amount_minor >= 0
        and isinstance(inputs.currency, str)
        and re.fullmatch(r"[A-Z]{3}", inputs.currency) is not None
    ):
        threshold = config.no_reference_step_up_thresholds_minor.get(inputs.currency)
        if threshold is None:
            reasons.append(ReasonCode.STEP_UP_THRESHOLD_NOT_CONFIGURED)
        elif inputs.amount_minor >= threshold:
            reasons.append(ReasonCode.NO_REFERENCE_OVER_THRESHOLD)

    # Priority 5: upstream errors/timeouts require a step-up.
    if inputs.upstream_failures:
        reasons.append(ReasonCode.UPSTREAM_FAILURE)

    block_reasons = {
        ReasonCode.HIGH_SEVERITY_CONFLICT,
        ReasonCode.WINNER_NOT_PERMITTED,
        ReasonCode.HARD_CONSTRAINT_VIOLATION,
    }
    if block_reasons.intersection(reasons):
        result = DecisionResult.BLOCK
    elif reasons:
        result = DecisionResult.STEP_UP
    else:
        result = DecisionResult.ALLOW
        reasons.append(ReasonCode.CHECKS_PASSED)

    decision = Decision(
        run_id=inputs.run_id,
        result=result,
        reasons=tuple(dict.fromkeys(reasons)),
        policy_version=config.effective_policy_version,
        amount_minor=(
            inputs.amount_minor
            if type(inputs.amount_minor) is int and inputs.amount_minor >= 0
            else None
        ),
        currency=(
            inputs.currency
            if isinstance(inputs.currency, str)
            and re.fullmatch(r"[A-Z]{3}", inputs.currency) is not None
            else None
        ),
        winner_fact_id=inputs.winner_fact_id,
    )
    approval_payload = {
        "schema": "warrant-policy-approval-v1",
        "run_id": decision.run_id,
        "winner_fact_id": decision.winner_fact_id,
        "result": decision.result.value,
        "reasons": [reason.value for reason in decision.reasons],
        "policy_version": decision.policy_version,
        "amount_minor": decision.amount_minor,
        "currency": decision.currency,
        "evidence": {
            "winner_candidate_id": (
                inputs.winner_candidate_id if isinstance(inputs.winner_candidate_id, str) else None
            ),
            "winner_permitted": (
                inputs.winner_permitted if type(inputs.winner_permitted) is bool else None
            ),
            "hard_constraints_satisfied": (
                inputs.hard_constraints_satisfied
                if type(inputs.hard_constraints_satisfied) is bool
                else None
            ),
            "stability_stable": (
                inputs.stability_stable if type(inputs.stability_stable) is bool else None
            ),
            "no_reference": inputs.no_reference if type(inputs.no_reference) is bool else None,
            "conflicts": [
                {
                    "field": conflict.field if isinstance(conflict.field, str) else None,
                    "severity": (
                        conflict.severity.value
                        if isinstance(conflict.severity, ConflictSeverity)
                        else None
                    ),
                    "fact_id": conflict.fact_id if isinstance(conflict.fact_id, str) else None,
                }
                for conflict in inputs.conflicts
                if isinstance(inputs.conflicts, tuple) and isinstance(conflict, FactConflict)
            ]
            if isinstance(inputs.conflicts, tuple)
            else None,
            "upstream_failures": [
                {
                    "stage": failure.stage if isinstance(failure.stage, str) else None,
                    "code": failure.code if isinstance(failure.code, str) else None,
                }
                for failure in inputs.upstream_failures
                if isinstance(inputs.upstream_failures, tuple)
                and isinstance(failure, UpstreamFailure)
            ]
            if isinstance(inputs.upstream_failures, tuple)
            else None,
        },
    }
    approval_hash = hashlib.sha256(
        json.dumps(
            approval_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return Decision(
        run_id=decision.run_id,
        result=decision.result,
        reasons=decision.reasons,
        policy_version=decision.policy_version,
        amount_minor=decision.amount_minor,
        currency=decision.currency,
        winner_fact_id=decision.winner_fact_id,
        approval_hash=approval_hash,
    )


def _input_error(inputs: PolicyInput) -> ReasonCode | None:
    if not isinstance(inputs.run_id, str) or not inputs.run_id.strip():
        return ReasonCode.INVALID_POLICY_INPUT
    if inputs.winner_candidate_id is not None and (
        not isinstance(inputs.winner_candidate_id, str) or not inputs.winner_candidate_id.strip()
    ):
        return ReasonCode.INVALID_POLICY_INPUT
    if inputs.winner_fact_id is not None and (
        not isinstance(inputs.winner_fact_id, str) or not inputs.winner_fact_id.strip()
    ):
        return ReasonCode.INVALID_POLICY_INPUT
    if inputs.winner_candidate_id is not None and inputs.winner_fact_id is None:
        return ReasonCode.REQUIRED_EVIDENCE_MISSING
    for flag in (
        inputs.winner_permitted,
        inputs.hard_constraints_satisfied,
        inputs.stability_stable,
        inputs.no_reference,
    ):
        if flag is not None and type(flag) is not bool:
            return ReasonCode.INVALID_POLICY_INPUT
    if inputs.amount_minor is not None and (
        type(inputs.amount_minor) is not int or inputs.amount_minor < 0
    ):
        return ReasonCode.INVALID_POLICY_INPUT
    if inputs.currency is not None and (
        not isinstance(inputs.currency, str) or re.fullmatch(r"[A-Z]{3}", inputs.currency) is None
    ):
        return ReasonCode.INVALID_POLICY_INPUT
    if (inputs.amount_minor is None) != (inputs.currency is None):
        return ReasonCode.REQUIRED_EVIDENCE_MISSING
    if inputs.amount_minor is None or inputs.currency is None:
        return ReasonCode.REQUIRED_EVIDENCE_MISSING
    if not isinstance(inputs.conflicts, tuple) or not isinstance(inputs.upstream_failures, tuple):
        return ReasonCode.INVALID_POLICY_INPUT
    for conflict in inputs.conflicts:
        if not isinstance(conflict, FactConflict) or not isinstance(
            conflict.severity, ConflictSeverity
        ):
            return ReasonCode.INVALID_POLICY_INPUT
        if not isinstance(conflict.field, str) or not conflict.field.strip():
            return ReasonCode.INVALID_POLICY_INPUT
    for failure in inputs.upstream_failures:
        if (
            not isinstance(failure, UpstreamFailure)
            or not isinstance(failure.stage, str)
            or not failure.stage.strip()
            or not isinstance(failure.code, str)
            or not failure.code.strip()
        ):
            return ReasonCode.INVALID_POLICY_INPUT
    return None
