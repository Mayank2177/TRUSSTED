from __future__ import annotations

import pytest

from warrant.policy.evaluate import decide
from warrant.policy.models import (
    ConflictSeverity,
    DecisionResult,
    FactConflict,
    PolicyConfig,
    PolicyInput,
    ReasonCode,
    UpstreamFailure,
)

CONFIG = PolicyConfig("policy-test-1", {"INR": 100_000, "USD": 10_000})


def valid_input(**changes: object) -> PolicyInput:
    values: dict[str, object] = {
        "run_id": "run-1",
        "winner_candidate_id": "ssd-a",
        "winner_permitted": True,
        "hard_constraints_satisfied": True,
        "stability_stable": True,
        "no_reference": False,
        "amount_minor": 99_999,
        "currency": "INR",
        "winner_fact_id": "fact-ssd-a",
        "conflicts": (),
        "upstream_failures": (),
    }
    values.update(changes)
    return PolicyInput(**values)  # type: ignore[arg-type]


def test_allow_when_all_checks_pass_and_is_repeatable() -> None:
    inputs = valid_input()
    first = decide(inputs, CONFIG)
    assert first == decide(inputs, CONFIG)
    assert first.result is DecisionResult.ALLOW
    assert first.reasons == (ReasonCode.CHECKS_PASSED,)
    assert first.policy_version == CONFIG.effective_policy_version
    assert first.winner_fact_id == "fact-ssd-a"
    assert len(first.approval_hash or "") == 64
    assert first.approval_hash == decide(inputs, CONFIG).approval_hash


def test_approval_hash_binds_winner_and_authorization_evidence() -> None:
    baseline = decide(valid_input(), CONFIG)
    changed_winner = decide(valid_input(winner_fact_id="fact-other"), CONFIG)
    changed_evidence = decide(valid_input(hard_constraints_satisfied=False), CONFIG)

    assert baseline.approval_hash != changed_winner.approval_hash
    assert baseline.approval_hash != changed_evidence.approval_hash


def test_missing_winner_fact_identity_cannot_allow() -> None:
    result = decide(valid_input(winner_fact_id=None), CONFIG)

    assert result.result is DecisionResult.STEP_UP
    assert ReasonCode.REQUIRED_EVIDENCE_MISSING in result.reasons


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (
            {"conflicts": (FactConflict("capacity", ConflictSeverity.HIGH),)},
            ReasonCode.HIGH_SEVERITY_CONFLICT,
        ),
        ({"winner_permitted": False}, ReasonCode.WINNER_NOT_PERMITTED),
        ({"hard_constraints_satisfied": False}, ReasonCode.HARD_CONSTRAINT_VIOLATION),
    ],
)
def test_each_block_rule(change: dict[str, object], reason: ReasonCode) -> None:
    result = decide(valid_input(**change), CONFIG)
    assert result.result is DecisionResult.BLOCK
    assert reason in result.reasons


def test_lower_severity_conflicts_do_not_block() -> None:
    result = decide(valid_input(conflicts=(FactConflict("rating", ConflictSeverity.LOW),)), CONFIG)
    assert result.result is DecisionResult.ALLOW


def test_instability_steps_up() -> None:
    result = decide(valid_input(stability_stable=False), CONFIG)
    assert result.result is DecisionResult.STEP_UP
    assert ReasonCode.WINNER_UNSTABLE in result.reasons


@pytest.mark.parametrize("amount", [100_000, 100_001])
def test_no_reference_at_or_above_threshold_steps_up(amount: int) -> None:
    result = decide(valid_input(no_reference=True, amount_minor=amount), CONFIG)
    assert result.result is DecisionResult.STEP_UP
    assert ReasonCode.NO_REFERENCE_OVER_THRESHOLD in result.reasons


def test_no_reference_below_threshold_does_not_step_up_by_itself() -> None:
    result = decide(valid_input(no_reference=True, amount_minor=99_999), CONFIG)
    assert result.result is DecisionResult.ALLOW


def test_currency_specific_threshold_is_used() -> None:
    result = decide(valid_input(no_reference=True, amount_minor=10_000, currency="USD"), CONFIG)
    assert result.result is DecisionResult.STEP_UP


def test_missing_threshold_fails_closed() -> None:
    result = decide(valid_input(no_reference=True, currency="EUR"), CONFIG)
    assert result.result is DecisionResult.STEP_UP
    assert ReasonCode.STEP_UP_THRESHOLD_NOT_CONFIGURED in result.reasons


def test_upstream_failure_steps_up() -> None:
    result = decide(valid_input(upstream_failures=(UpstreamFailure("stage4", "TIMEOUT"),)), CONFIG)
    assert result.result is DecisionResult.STEP_UP
    assert ReasonCode.UPSTREAM_FAILURE in result.reasons


def test_block_rules_take_priority_but_all_triggers_are_reported() -> None:
    result = decide(
        valid_input(
            conflicts=(FactConflict("price", ConflictSeverity.HIGH),),
            stability_stable=False,
            upstream_failures=(UpstreamFailure("stage4", "ERROR"),),
        ),
        CONFIG,
    )
    assert result.result is DecisionResult.BLOCK
    assert ReasonCode.HIGH_SEVERITY_CONFLICT in result.reasons
    assert ReasonCode.WINNER_UNSTABLE in result.reasons
    assert ReasonCode.UPSTREAM_FAILURE in result.reasons


def test_constraint_block_has_priority_over_unstable_step_up() -> None:
    result = decide(valid_input(hard_constraints_satisfied=False, stability_stable=False), CONFIG)
    assert result.result is DecisionResult.BLOCK


@pytest.mark.parametrize(
    "change",
    [
        {"winner_candidate_id": None},
        {"winner_permitted": None},
        {"hard_constraints_satisfied": None},
        {"stability_stable": None},
        {"no_reference": None},
        {"amount_minor": None, "currency": None},
        {"currency": "inr"},
        {"amount_minor": 12.5},
        {"winner_permitted": 1},
        {"amount_minor": [1], "no_reference": True},
        {"currency": ["INR"], "no_reference": True},
    ],
)
def test_missing_or_invalid_evidence_never_allows(change: dict[str, object]) -> None:
    result = decide(valid_input(**change), CONFIG)
    assert result.result is DecisionResult.STEP_UP
    assert result.reasons
    if isinstance(change.get("amount_minor"), list):
        assert result.amount_minor is None
    if isinstance(change.get("currency"), list):
        assert result.currency is None


def test_policy_config_rejects_float_threshold() -> None:
    with pytest.raises(ValueError):
        PolicyConfig("v1", {"INR": 1.5})  # type: ignore[dict-item]


def test_policy_version_fingerprint_changes_with_threshold_configuration() -> None:
    first = PolicyConfig("policy-1", {"INR": 10_000, "USD": 5_000})
    same_values_different_order = PolicyConfig("policy-1", {"USD": 5_000, "INR": 10_000})
    changed_threshold = PolicyConfig("policy-1", {"INR": 10_001, "USD": 5_000})

    assert first.effective_policy_version == same_values_different_order.effective_policy_version
    assert first.effective_policy_version != changed_threshold.effective_policy_version


def test_untyped_conflict_severity_fails_closed() -> None:
    result = decide(
        valid_input(conflicts=(FactConflict("capacity", "high"),)),  # type: ignore[arg-type]
        CONFIG,
    )
    assert result.result is DecisionResult.STEP_UP
    assert ReasonCode.INVALID_POLICY_INPUT in result.reasons


def test_non_tuple_evidence_fails_closed_without_crashing() -> None:
    result = decide(valid_input(conflicts=None), CONFIG)  # type: ignore[arg-type]
    assert result.result is DecisionResult.STEP_UP
    assert ReasonCode.INVALID_POLICY_INPUT in result.reasons


@pytest.mark.parametrize(
    ("inputs", "config"),
    [(None, CONFIG), (valid_input(), None)],
)
def test_invalid_top_level_policy_objects_fail_closed(inputs, config) -> None:
    result = decide(inputs, config)  # type: ignore[arg-type]
    assert result.result is DecisionResult.STEP_UP
    assert result.reasons == (ReasonCode.INVALID_POLICY_INPUT,)
