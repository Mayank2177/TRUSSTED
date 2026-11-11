"""Trusted evidence assembly tests use deliberately synthetic, run-scoped identities."""

from dataclasses import replace

import pytest

from warrant.integrity.contracts import ExtractionResult, ProductFact, RankingResult, UserIntent
from warrant.integrity.engine import (
    PerturbationOutcome,
    PerturbationType,
    StabilityReport,
    StabilityState,
)
from warrant.policy.evidence import (
    EvidenceAssemblyError,
    SameRunEvidence,
    evaluate_same_run,
)
from warrant.policy.models import DecisionResult, PolicyConfig, PolicyInput


def _evidence(
    *,
    run_id: str = "synthetic-run-1",
    stability_state: StabilityState = StabilityState.COMPLETED,
    sku: str | None = "synthetic-sku-1",
    seller_id: str = "synthetic-seller-1",
) -> SameRunEvidence:
    fact = ProductFact(
        candidate_id="synthetic-candidate-1",
        name="Synthetic SSD",
        price_minor=9_500,
        currency="INR",
        seller_id=seller_id,
        spec={"capacity_gb": "1000"},
        sku=sku,
    )
    extraction = ExtractionResult(run_id, (fact.candidate_id,), (fact,))
    ranking = RankingResult(run_id, fact.candidate_id, (fact.candidate_id,))
    outcomes = (
        (
            PerturbationOutcome(
                PerturbationType.STRIP_PERSUASION,
                "synthetic-strip-run",
                None,
                fact.candidate_id,
                True,
                False,
            ),
            PerturbationOutcome(
                PerturbationType.SHUFFLE_ORDER,
                "synthetic-shuffle-run",
                0,
                fact.candidate_id,
                True,
                True,
            ),
        )
        if stability_state is StabilityState.COMPLETED
        else ()
    )
    planned_count = len(outcomes)
    stability = StabilityReport(
        run_id=run_id,
        state=stability_state,
        skip_reason="synthetic cost skip" if stability_state is StabilityState.SKIPPED else None,
        baseline_winner_id=fact.candidate_id,
        winner_counts=((fact.candidate_id, planned_count),) if planned_count else (),
        stable=stability_state is StabilityState.COMPLETED,
        threshold=1.0,
        planned_count=planned_count,
        successful_count=planned_count,
        failed_count=0,
        changed_count=1 if planned_count else 0,
        shuffle_changed_count=1 if planned_count else 0,
        outcomes=outcomes,
        winner_flips=(),
        errors=(),
    )
    intent = UserIntent(
        max_price_minor=10_000,
        currency="INR",
        required_specs={"capacity_gb": "1000"},
        allowed_merchants=(seller_id,),
        weights={},
    )
    return SameRunEvidence(
        run_id=run_id,
        extraction=extraction,
        ranking=ranking,
        stability=stability,
        intent=intent,
        persisted_fact_id_by_candidate={fact.candidate_id: "synthetic-db-fact-1"},
        no_reference_by_candidate={fact.candidate_id: False},
    )


POLICY = PolicyConfig("synthetic-policy-v1", {"INR": 100_000})


def test_same_run_evidence_derives_allow_and_persisted_winner_identity() -> None:
    result = evaluate_same_run(_evidence(), POLICY)

    assert result.decision.result is DecisionResult.ALLOW
    assert result.decision.winner_fact_id == "synthetic-db-fact-1"
    assert result.winner_candidate_id == "synthetic-candidate-1"
    assert result.seller_id == "synthetic-seller-1"
    assert result.sku == "synthetic-sku-1"


@pytest.mark.parametrize(
    "changes",
    [
        {
            "ranking": RankingResult(
                "other-run", "synthetic-candidate-1", ("synthetic-candidate-1",)
            )
        },
        {"persisted_fact_id_by_candidate": {}},
    ],
)
def test_cross_run_or_unmapped_evidence_is_rejected(changes: dict[str, object]) -> None:
    evidence = replace(_evidence(), **changes)

    with pytest.raises(EvidenceAssemblyError):
        evaluate_same_run(evidence, POLICY)


@pytest.mark.parametrize(
    ("seller_id", "sku"),
    [("", "synthetic-sku-1"), ("synthetic-seller-1", None)],
)
def test_missing_seller_or_sku_fails_closed(seller_id: str, sku: str | None) -> None:
    if not seller_id:
        with pytest.raises(ValueError, match="seller_id"):
            ProductFact(
                candidate_id="synthetic-candidate-1",
                name="Synthetic SSD",
                price_minor=9_500,
                currency="INR",
                seller_id="",
                spec={"capacity_gb": "1000"},
                sku=sku,
            )
        return
    evidence = _evidence(seller_id=seller_id, sku=sku)
    fact = evidence.extraction.facts[0]
    evidence = replace(evidence, extraction=replace(evidence.extraction, facts=(fact,)))
    with pytest.raises(EvidenceAssemblyError, match="seller and SKU"):
        evaluate_same_run(evidence, POLICY)


def test_policy_evaluator_input_is_not_accepted_as_trusted_stage_evidence() -> None:
    untrusted_input = PolicyInput("run", "winner", True, True, True, False, 1, "INR")

    with pytest.raises(EvidenceAssemblyError):
        evaluate_same_run(untrusted_input, POLICY)  # type: ignore[arg-type]


def test_skipped_stability_is_a_step_up_and_never_an_allow() -> None:
    evidence = _evidence(stability_state=StabilityState.SKIPPED)

    result = evaluate_same_run(evidence, POLICY).decision

    assert result.result is DecisionResult.STEP_UP


@pytest.mark.parametrize(
    "defect",
    [
        "empty outcomes",
        "missing outcome",
        "failed outcome",
        "wrong winner",
        "zero meaningful shuffles",
        "incomplete perturbation count",
        "invalid threshold",
    ],
)
def test_incomplete_stability_evidence_never_allows(defect: str) -> None:
    report = _evidence().stability
    strip, shuffle = report.outcomes
    if defect == "empty outcomes":
        report = replace(report, outcomes=())
    elif defect == "missing outcome":
        report = replace(report, outcomes=(strip,))
    elif defect == "failed outcome":
        failed = replace(shuffle, succeeded=False, error_code="UPSTREAM_ERROR")
        report = replace(
            report,
            state=StabilityState.FAILED,
            outcomes=(strip, failed),
            successful_count=1,
            failed_count=1,
            stable=False,
        )
    elif defect == "wrong winner":
        report = replace(
            report,
            outcomes=(strip, replace(shuffle, winner_candidate_id="other-candidate")),
        )
    elif defect == "zero meaningful shuffles":
        report = replace(
            report,
            outcomes=(strip, replace(shuffle, changed_input=False)),
            changed_count=0,
            shuffle_changed_count=0,
        )
    elif defect == "incomplete perturbation count":
        report = replace(report, planned_count=3)
    else:
        report = replace(report, threshold=0.8)

    evidence = replace(_evidence(), stability=report)
    decision = evaluate_same_run(evidence, POLICY).decision

    assert decision.result is DecisionResult.STEP_UP, defect
