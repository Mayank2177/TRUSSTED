"""Trusted Stage 5 evidence assembly from validated same-run stage outputs.

This module is the application boundary between Stage 1–4 adapters and the pure policy
evaluator. It derives policy booleans from typed evidence rather than accepting a ready-made
``PolicyInput`` from an API caller. It does not turn caller-provided identifiers into proof:
the candidate-to-persisted-fact and seller mappings must come from an authoritative adapter.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from warrant.integrity.contracts import ExtractionResult, ProductFact, RankingResult, UserIntent
from warrant.integrity.engine import (
    PerturbationOutcome,
    PerturbationType,
    StabilityReport,
    StabilityState,
)
from warrant.policy.evaluate import decide
from warrant.policy.models import (
    Decision,
    FactConflict,
    PolicyConfig,
    PolicyInput,
    UpstreamFailure,
)


class EvidenceAssemblyError(ValueError):
    """Stage outputs cannot establish a complete, unambiguous same-run authorization."""


@dataclass(frozen=True, slots=True)
class SameRunEvidence:
    """Validated outputs and adapter-owned identity mappings for one pipeline run."""

    run_id: str
    extraction: ExtractionResult
    ranking: RankingResult
    stability: StabilityReport
    intent: UserIntent
    persisted_fact_id_by_candidate: Mapping[str, str]
    no_reference_by_candidate: Mapping[str, bool]
    conflicts: tuple[FactConflict, ...] = ()
    upstream_failures: tuple[UpstreamFailure, ...] = ()


@dataclass(frozen=True, slots=True)
class EvaluatedEvidence:
    """Decision plus the exact selected product details used to derive its policy input."""

    decision: Decision
    winner_candidate_id: str
    seller_id: str
    sku: str


class SameRunPolicyEvaluator(Protocol):
    """Replaceable typed application interface for policy evaluation from stage evidence."""

    def __call__(self, evidence: SameRunEvidence, config: PolicyConfig) -> EvaluatedEvidence: ...


def evaluate_same_run(evidence: SameRunEvidence, config: PolicyConfig) -> EvaluatedEvidence:
    """Validate ownership, derive constraints, and invoke the single deterministic evaluator.

    Missing seller/SKU, cross-run results, skipped stability, or incomplete authoritative
    mappings fail closed by raising ``EvidenceAssemblyError``; callers must not issue a token
    when assembly fails.
    """
    if not isinstance(evidence, SameRunEvidence) or not isinstance(config, PolicyConfig):
        raise EvidenceAssemblyError("validated same-run evidence and policy config are required")
    run_id = evidence.run_id
    if not isinstance(run_id, str) or not run_id.strip():
        raise EvidenceAssemblyError("run identifier is missing")
    extraction, ranking, stability, intent = (
        evidence.extraction,
        evidence.ranking,
        evidence.stability,
        evidence.intent,
    )
    if (
        not isinstance(extraction, ExtractionResult)
        or not isinstance(ranking, RankingResult)
        or extraction.run_id != run_id
        or ranking.run_id != run_id
        or not isinstance(stability, StabilityReport)
        or stability.run_id != run_id
    ):
        raise EvidenceAssemblyError("stage outputs do not belong to the same run")
    if (
        not isinstance(extraction.candidate_ids, tuple)
        or not extraction.candidate_ids
        or any(
            not isinstance(value, str) or not value.strip() for value in extraction.candidate_ids
        )
        or len(set(extraction.candidate_ids)) != len(extraction.candidate_ids)
        or not isinstance(extraction.facts, tuple)
        or any(
            not isinstance(fact, ProductFact) or fact.candidate_id not in extraction.candidate_ids
            for fact in extraction.facts
        )
        or not isinstance(ranking.ranked_candidate_ids, tuple)
        or any(
            not isinstance(value, str) or not value.strip()
            for value in ranking.ranked_candidate_ids
        )
        or len(set(ranking.ranked_candidate_ids)) != len(ranking.ranked_candidate_ids)
        or not set(ranking.ranked_candidate_ids).issubset(extraction.candidate_ids)
    ):
        raise EvidenceAssemblyError("extraction or ranking membership is invalid")
    winner = ranking.winner_candidate_id
    if not isinstance(winner, str) or not winner.strip():
        raise EvidenceAssemblyError("ranking has no winner")
    if winner not in extraction.candidate_ids or winner not in ranking.ranked_candidate_ids:
        raise EvidenceAssemblyError("ranked winner is not owned by this extraction")
    facts = [fact for fact in extraction.facts if fact.candidate_id == winner]
    if len(facts) != 1:
        raise EvidenceAssemblyError("winner fact is missing or ambiguous")
    fact = facts[0]
    if not fact.seller_id.strip() or not fact.sku:
        raise EvidenceAssemblyError("winner seller and SKU identity are required")
    if not isinstance(evidence.persisted_fact_id_by_candidate, Mapping):
        raise EvidenceAssemblyError("persisted fact mapping is invalid")
    fact_id = evidence.persisted_fact_id_by_candidate.get(winner)
    if not isinstance(fact_id, str) or not fact_id.strip():
        raise EvidenceAssemblyError("authoritative persisted winner fact ID is missing")
    if not isinstance(intent, UserIntent) or intent.currency != fact.currency:
        raise EvidenceAssemblyError("winner does not match validated intent currency")
    if (
        (
            intent.max_price_minor is not None
            and (type(intent.max_price_minor) is not int or intent.max_price_minor < 0)
        )
        or not isinstance(intent.required_specs, Mapping)
        or any(
            not isinstance(key, str) or not key or type(value) not in (str, int, bool)
            for key, value in intent.required_specs.items()
        )
        or not isinstance(intent.allowed_merchants, (tuple, type(None)))
        or (
            intent.allowed_merchants is not None
            and any(not isinstance(value, str) or not value for value in intent.allowed_merchants)
        )
    ):
        raise EvidenceAssemblyError("intent constraints are invalid")

    allowed = intent.allowed_merchants
    permitted = allowed is None or fact.seller_id in allowed
    constraints = (
        intent.max_price_minor is None or fact.price_minor <= intent.max_price_minor
    ) and all(fact.spec.get(name) == expected for name, expected in intent.required_specs.items())

    complete_stability = _complete_stability(stability, run_id=run_id, winner=winner)
    stable = stability.stable if complete_stability else None
    if not isinstance(evidence.no_reference_by_candidate, Mapping):
        raise EvidenceAssemblyError("reference evidence mapping is invalid")
    no_reference = evidence.no_reference_by_candidate.get(winner)
    if type(no_reference) is not bool:
        no_reference = None
    if (
        not isinstance(evidence.conflicts, tuple)
        or not isinstance(evidence.upstream_failures, tuple)
        or any(not isinstance(conflict, FactConflict) for conflict in evidence.conflicts)
        or any(not isinstance(failure, UpstreamFailure) for failure in evidence.upstream_failures)
    ):
        raise EvidenceAssemblyError("conflict or failure evidence is invalid")
    failures = evidence.upstream_failures
    if not complete_stability:
        failures += (UpstreamFailure("stage4", "STABILITY_UNAVAILABLE_OR_MISMATCHED"),)

    policy_input = PolicyInput(
        run_id=run_id,
        winner_candidate_id=winner,
        winner_permitted=permitted,
        hard_constraints_satisfied=constraints,
        stability_stable=stable,
        no_reference=no_reference,
        amount_minor=fact.price_minor,
        currency=fact.currency,
        conflicts=evidence.conflicts,
        upstream_failures=failures,
        winner_fact_id=fact_id,
    )
    return EvaluatedEvidence(
        decision=decide(policy_input, config),
        winner_candidate_id=winner,
        seller_id=fact.seller_id,
        sku=fact.sku,
    )


def _complete_stability(stability: StabilityReport, *, run_id: str, winner: str) -> bool:
    """Accept only a complete strict-100% Stage 4 plan with a real changed shuffle.

    The report's threshold is fixed by ``StabilityConfig`` at 1.0. In addition to the
    aggregate counters, validate the per-outcome evidence so a forged or partial summary
    cannot turn missing/failed perturbations into a stable result.
    """
    outcomes = stability.outcomes
    if (
        stability.state is not StabilityState.COMPLETED
        or stability.run_id != run_id
        or stability.baseline_winner_id != winner
        or stability.skip_reason is not None
        or type(stability.stable) is not bool
        or stability.stable is not True
        or type(stability.threshold) not in (int, float)
        or stability.threshold != 1.0
        or type(stability.planned_count) is not int
        or stability.planned_count < 2
        or not isinstance(outcomes, tuple)
        or len(outcomes) != stability.planned_count
        or type(stability.successful_count) is not int
        or stability.successful_count != stability.planned_count
        or type(stability.failed_count) is not int
        or stability.failed_count != 0
        or not isinstance(stability.winner_flips, tuple)
        or stability.winner_flips
        or not isinstance(stability.errors, tuple)
        or stability.errors
    ):
        return False

    if any(not isinstance(outcome, PerturbationOutcome) for outcome in outcomes):
        return False
    run_ids = tuple(outcome.run_id for outcome in outcomes)
    if any(
        not isinstance(item, str) or not item.strip() or item == run_id for item in run_ids
    ) or len(set(run_ids)) != len(run_ids):
        return False
    if any(
        type(outcome.succeeded) is not bool
        or outcome.succeeded is not True
        or outcome.winner_candidate_id != winner
        or type(outcome.changed_input) is not bool
        or outcome.error_code is not None
        or outcome.error_message is not None
        for outcome in outcomes
    ):
        return False

    strips = tuple(
        outcome for outcome in outcomes if outcome.perturbation is PerturbationType.STRIP_PERSUASION
    )
    shuffles = tuple(
        outcome for outcome in outcomes if outcome.perturbation is PerturbationType.SHUFFLE_ORDER
    )
    if len(strips) != 1 or len(shuffles) < 1 or len(strips) + len(shuffles) != len(outcomes):
        return False
    if strips[0].seed is not None:
        return False
    shuffle_seeds = tuple(outcome.seed for outcome in shuffles)
    if any(type(seed) is not int for seed in shuffle_seeds) or len(set(shuffle_seeds)) != len(
        shuffle_seeds
    ):
        return False

    changed_count = sum(outcome.changed_input for outcome in outcomes)
    shuffle_changed_count = sum(outcome.changed_input for outcome in shuffles)
    if (
        type(stability.changed_count) is not int
        or stability.changed_count != changed_count
        or type(stability.shuffle_changed_count) is not int
        or stability.shuffle_changed_count != shuffle_changed_count
        or shuffle_changed_count < 1
    ):
        return False

    if not isinstance(stability.winner_counts, tuple):
        return False
    if stability.winner_counts != ((winner, stability.planned_count),):
        return False
    return True
