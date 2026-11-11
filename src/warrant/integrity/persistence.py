"""Explicit mapping from Stage 4 outputs into the canonical warrant.db repositories."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from uuid import uuid4

from pydantic import JsonValue
from sqlalchemy.orm import Session

from warrant.db.contracts.evidence import ProductFactInput, RankingInput
from warrant.db.contracts.outcomes import StabilityInput
from warrant.db.contracts.runs import StageState
from warrant.db.repositories.evidence import save_product_facts, save_ranking
from warrant.db.repositories.outcomes import save_stability_report
from warrant.db.repositories.runs import record_stage_state
from warrant.integrity.contracts import RankingResult
from warrant.integrity.engine import StabilityReport, StabilityState

type StableProductIdentity = tuple[str, str]


def persist_perturbation_facts(
    session: Session,
    *,
    parent_run_id: str,
    facts: tuple[ProductFactInput, ...],
    stable_identity_by_fact_id: Mapping[str, StableProductIdentity],
) -> Mapping[StableProductIdentity, str]:
    """Persist per-extraction fact IDs while validating explicit seller/SKU correlation.

    The caller first persists each observation in the parent run. Every fact keeps its
    extraction-specific ID; the returned map is the only supported way to correlate
    equivalent products between perturbations. Missing or duplicate seller/SKU identities
    fail closed. Product identity is never inferred from fact IDs or URLs.
    """
    if not facts:
        raise ValueError("an extraction must contain at least one persisted product fact")
    fact_ids = [fact.id for fact in facts]
    if len(set(fact_ids)) != len(fact_ids):
        raise ValueError("extraction fact IDs must be distinct")
    if set(fact_ids) != set(stable_identity_by_fact_id):
        raise ValueError("every fact requires exactly one explicit stable identity mapping")
    identity_by_product: dict[StableProductIdentity, str] = {}
    for fact in facts:
        identity = stable_identity_by_fact_id[fact.id]
        if (
            not isinstance(identity, tuple)
            or len(identity) != 2
            or identity != (fact.seller_id, fact.sku)
        ):
            raise ValueError("stable identity must exactly match the persisted seller and SKU")
        if identity in identity_by_product:
            raise ValueError("seller/SKU identity is ambiguous within one extraction")
        if fact.run_id != parent_run_id:
            raise ValueError("perturbation facts must be stored under the parent run")
        identity_by_product[identity] = fact.id
    save_product_facts(session, facts)
    return identity_by_product


def candidate_fact_mapping(
    *,
    candidate_id_by_identity: Mapping[StableProductIdentity, str],
    fact_id_by_identity: Mapping[StableProductIdentity, str],
) -> Mapping[str, str]:
    """Build an explicit per-run candidate-to-fact map through agreed stable identities."""
    if len(set(candidate_id_by_identity.values())) != len(candidate_id_by_identity):
        raise ValueError("stable product identities cannot share a candidate ID")
    missing = set(candidate_id_by_identity).difference(fact_id_by_identity)
    if missing:
        raise ValueError("every ranked stable identity must map to a persisted fact")
    return {
        candidate_id: fact_id_by_identity[identity]
        for identity, candidate_id in candidate_id_by_identity.items()
    }


def persist_ranking(
    session: Session,
    *,
    run_id: str,
    perturbation: str,
    ranking: RankingResult,
    fact_id_by_candidate_id: Mapping[str, str],
    score_by_candidate_id: Mapping[str, float] | None = None,
    ranking_id: str | None = None,
) -> str:
    """Persist rank order only after an explicit candidate-to-run-fact mapping is supplied."""
    if ranking.run_id != run_id:
        raise ValueError("ranking run ID does not match the persistence parent run")
    if re.fullmatch(r"(?:none|strip_persuasion|shuffle_[0-9]+)", perturbation) is None:
        raise ValueError("perturbation must use the shared none/strip_persuasion/shuffle_i labels")
    if not ranking.ranked_candidate_ids:
        raise ValueError("cannot persist an empty ranking")
    if len(set(ranking.ranked_candidate_ids)) != len(ranking.ranked_candidate_ids):
        raise ValueError("ranking candidates must be distinct")
    missing = set(ranking.ranked_candidate_ids).difference(fact_id_by_candidate_id)
    if missing:
        raise ValueError("every ranked candidate needs an explicit same-run fact ID mapping")
    fact_ids = tuple(fact_id_by_candidate_id[item] for item in ranking.ranked_candidate_ids)
    if len(set(fact_ids)) != len(fact_ids):
        raise ValueError("distinct ranked products cannot map to the same fact ID")
    winner_id = ranking.winner_candidate_id
    if winner_id is not None and winner_id not in ranking.ranked_candidate_ids:
        raise ValueError("ranking winner is absent from its ranked candidates")
    scores = score_by_candidate_id or {}
    if set(scores).difference(ranking.ranked_candidate_ids):
        raise ValueError("scores must refer to ranked candidates")
    value = RankingInput(
        id=ranking_id or uuid4().hex,
        run_id=run_id,
        perturbation=perturbation,
        ordered_fact_ids=fact_ids,
        scores={fact_id_by_candidate_id[key]: score for key, score in scores.items()},
        winner_fact_id=fact_id_by_candidate_id[winner_id] if winner_id is not None else None,
    )
    return save_ranking(session, value)


def persist_stability_report(
    session: Session,
    *,
    report: StabilityReport,
    parent_run_id: str,
    base_fact_id_by_candidate_id: Mapping[str, str],
    report_id: str | None = None,
) -> str | None:
    """Persist completed evidence or explicit skipped/error/timeout stage state.

    Callback sub-run IDs are retained as correlation strings in `flips`; they are never
    passed to a repository as database run IDs. Candidate IDs map only through the
    caller-supplied base-run mapping, whose facts are checked by the shared repository.
    """
    if report.run_id != parent_run_id:
        raise ValueError("stability report run ID does not match the parent run")
    if report.state is StabilityState.SKIPPED:
        record_stage_state(
            session,
            parent_run_id,
            StageState(stage="perturb", state="skipped", reason_code=report.skip_reason),
        )
        return None
    if report.state is StabilityState.FAILED:
        timeout = any(outcome.error_code == "TIMEOUT" for outcome in report.outcomes)
        record_stage_state(
            session,
            parent_run_id,
            StageState(
                stage="perturb",
                state="timeout" if timeout else "error",
                reason_code="PERTURBATION_TIMEOUT" if timeout else "PERTURBATION_FAILED",
            ),
        )
        return None

    if report.state is not StabilityState.COMPLETED:
        raise ValueError("unknown stability report state")
    if report.baseline_winner_id is None:
        raise ValueError("completed stability report requires a baseline winner")
    candidate_ids = {candidate for candidate, _ in report.winner_counts}
    candidate_ids.add(report.baseline_winner_id)
    candidate_ids.update(
        outcome.winner_candidate_id
        for outcome in report.outcomes
        if outcome.winner_candidate_id is not None
    )
    if candidate_ids.difference(base_fact_id_by_candidate_id):
        raise ValueError("stability winners require explicit parent-run fact mappings")
    mapped_fact_ids = [base_fact_id_by_candidate_id[key] for key in candidate_ids]
    if len(set(mapped_fact_ids)) != len(mapped_fact_ids):
        raise ValueError("distinct stable product identities cannot share a parent fact ID")
    counts: Counter[str] = Counter()
    for candidate_id, count in report.winner_counts:
        if type(count) is not int or count < 0:
            raise ValueError("winner counts must be non-negative integers")
        counts[base_fact_id_by_candidate_id[candidate_id]] += count
    flips: dict[str, JsonValue] = {
        "schema": "warrant-stability-report-v1",
        "baseline_winner_fact_id": base_fact_id_by_candidate_id[report.baseline_winner_id],
        "winner_flip_sub_run_ids": list(report.winner_flips),
        "outcomes": [
            {
                "kind": outcome.perturbation.value,
                "sub_run_id": outcome.run_id,
                "seed": outcome.seed,
                "winner_fact_id": (
                    base_fact_id_by_candidate_id.get(outcome.winner_candidate_id)
                    if outcome.winner_candidate_id is not None
                    else None
                ),
                "succeeded": outcome.succeeded,
                "changed_input": outcome.changed_input,
                "error_code": outcome.error_code,
            }
            for outcome in report.outcomes
        ],
        "errors": list(report.errors),
        "planned_count": report.planned_count,
        "successful_count": report.successful_count,
        "failed_count": report.failed_count,
        "changed_count": report.changed_count,
        "shuffle_changed_count": report.shuffle_changed_count,
    }
    return save_stability_report(
        session,
        StabilityInput(
            id=report_id or uuid4().hex,
            run_id=parent_run_id,
            winner_counts=dict(counts),
            stable=report.stable,
            threshold=report.threshold,
            flips=flips,
        ),
    )
