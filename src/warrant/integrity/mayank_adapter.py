"""Strict adapters for the concrete Stage 1–3 output shapes in Mayank's archive.

This module uses structural protocols so the Stage 4 package does not vendor or import a
second copy of Mayank's ``trussted`` package. It deliberately requires caller-supplied
candidate and actual-seller mappings: the archive's fact ID changes with page content, and its
``merchant_id`` is derived from the page URL rather than identifying the marketplace seller.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Protocol

from warrant.integrity.contracts import ExtractionResult, ProductFact, RankingResult
from warrant.policy.models import ConflictSeverity, FactConflict, UpstreamFailure


class MayankMoney(Protocol):
    amount_minor: int
    currency: str


class MayankFact(Protocol):
    """Structural view of ``trussted.models.facts.ProductFact``."""

    fact_id: str
    observation_id: str
    merchant_id: str
    name: str
    price: MayankMoney
    brand: str | None
    sku: str | None
    gtin: str | None
    shipping: MayankMoney | None
    additional_charges: MayankMoney | None
    delivery_days: int | None
    rating: Decimal | None
    condition: str
    specs: Mapping[str, str]


class MayankRanked(Protocol):
    fact: MayankFact


class MayankRanking(Protocol):
    ranked: Sequence[MayankRanked]
    winner_fact_id: str | None


class MayankStageError(Protocol):
    stage: str


class MayankConflict(Protocol):
    field: str
    severity: str
    fact_id: str


class MayankVerification(Protocol):
    fact_id: str
    status: str
    conflicts: Sequence[MayankConflict]
    independent_sources: Sequence[str]


class MayankSelection(Protocol):
    """Structural view of ``trussted.models.results.SelectionResult``."""

    facts: Sequence[MayankFact]
    ranking: MayankRanking
    stage_errors: Sequence[MayankStageError]
    verifications: Sequence[MayankVerification]


@dataclass(frozen=True, slots=True)
class AdaptedMayankSelection:
    """Stage 4-compatible facts/ranking plus sanitized upstream failure indicators."""

    extraction: ExtractionResult
    ranking: RankingResult
    upstream_failures: tuple[UpstreamFailure, ...]
    conflicts: tuple[FactConflict, ...]
    no_reference_by_candidate_id: Mapping[str, bool]


def adapt_mayank_selection(
    selection: MayankSelection,
    *,
    run_id: str,
    candidate_id_by_fact_id: Mapping[str, str],
    seller_id_by_fact_id: Mapping[str, str],
) -> AdaptedMayankSelection:
    """Adapt Mayank's actual fact/rank output without deriving product or seller identity.

    Both mapping arguments must be supplied by an integration layer using authoritative source
    evidence. Mayank's URL-derived merchant ID and content-derived fact ID are intentionally not
    used as either stable candidate identity or actual seller identity. The archive's
    observations do not retain typed visible-content blocks, so this adapter does not claim to
    make the output sufficient for a Stage 4 perturbation run.
    """
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id must be non-empty text")

    facts = tuple(selection.facts)
    fact_ids = tuple(fact.fact_id for fact in facts)
    if any(not isinstance(fact_id, str) or not fact_id.strip() for fact_id in fact_ids):
        raise ValueError("Mayank output contains an invalid fact ID")
    if len(fact_ids) != len(set(fact_ids)):
        raise ValueError("Mayank output contains duplicate fact IDs")

    expected_ids = set(fact_ids)
    if set(candidate_id_by_fact_id) != expected_ids:
        raise ValueError("candidate mapping must cover exactly the Mayank fact IDs")
    if set(seller_id_by_fact_id) != expected_ids:
        raise ValueError("actual-seller mapping must cover exactly the Mayank fact IDs")
    candidate_ids = tuple(candidate_id_by_fact_id[fact_id] for fact_id in fact_ids)
    seller_ids = tuple(seller_id_by_fact_id[fact_id] for fact_id in fact_ids)
    if any(not isinstance(value, str) or not value.strip() for value in candidate_ids):
        raise ValueError("candidate IDs must be non-empty authoritative mappings")
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("candidate mapping must be one-to-one for this selection")
    if any(not isinstance(value, str) or not value.strip() for value in seller_ids):
        raise ValueError("actual seller IDs must be non-empty authoritative mappings")
    if set(candidate_ids).intersection(fact_ids):
        raise ValueError("content-derived Mayank fact IDs are not stable candidate IDs")
    if any(
        seller_id == fact.merchant_id for fact, seller_id in zip(facts, seller_ids, strict=True)
    ):
        raise ValueError("Mayank URL-derived merchant IDs are not verified seller IDs")

    fact_by_id = {fact.fact_id: fact for fact in facts}
    candidate_by_fact_id = dict(zip(fact_ids, candidate_ids, strict=True))
    adapted_facts = tuple(
        ProductFact(
            candidate_id=candidate_by_fact_id[fact.fact_id],
            name=fact.name,
            price_minor=fact.price.amount_minor,
            currency=fact.price.currency,
            seller_id=seller_id_by_fact_id[fact.fact_id],
            spec=dict(fact.specs),
            sku=fact.sku,
            gtin=fact.gtin,
            # Mayank's evidence is quoted text, not a validated source offset.
            source_span=None,
            shipping_minor=(fact.shipping.amount_minor if fact.shipping is not None else None),
            additional_charges_minor=(
                fact.additional_charges.amount_minor
                if fact.additional_charges is not None
                else None
            ),
        )
        for fact in facts
    )

    ranked_fact_ids = tuple(item.fact.fact_id for item in selection.ranking.ranked)
    if len(ranked_fact_ids) != len(set(ranked_fact_ids)):
        raise ValueError("Mayank ranking contains duplicate fact IDs")
    if any(fact_id not in fact_by_id for fact_id in ranked_fact_ids):
        raise ValueError("Mayank ranking references a fact outside its selection")
    winner_fact_id = selection.ranking.winner_fact_id
    if winner_fact_id is not None and winner_fact_id not in ranked_fact_ids:
        raise ValueError("Mayank winner is absent from the ranked facts")
    if ranked_fact_ids and winner_fact_id != ranked_fact_ids[0]:
        raise ValueError("Mayank winner does not match the first ranked fact")
    if not ranked_fact_ids and winner_fact_id is not None:
        raise ValueError("Mayank returned a winner without ranked candidates")

    no_reference = {candidate_id: True for candidate_id in candidate_ids}
    seen_verifications: set[str] = set()
    adapted_conflicts: list[FactConflict] = []
    for verification in selection.verifications:
        fact_id = verification.fact_id
        if fact_id not in fact_by_id or fact_id in seen_verifications:
            raise ValueError("Mayank verification has an unknown or duplicate fact ID")
        if verification.status not in {"verified", "conflict", "no_reference"}:
            raise ValueError("Mayank verification has an unknown status")
        seen_verifications.add(fact_id)
        no_reference[candidate_by_fact_id[fact_id]] = (
            verification.status == "no_reference" or not verification.independent_sources
        )
        for conflict in verification.conflicts:
            if (
                conflict.fact_id != fact_id
                or not isinstance(conflict.field, str)
                or not conflict.field.strip()
            ):
                raise ValueError("Mayank conflict does not match its verified fact")
            try:
                severity = ConflictSeverity(conflict.severity)
            except (TypeError, ValueError) as error:
                raise ValueError("Mayank conflict has an unknown severity") from error
            adapted_conflicts.append(
                FactConflict(
                    field=conflict.field,
                    severity=severity,
                    fact_id=candidate_by_fact_id[fact_id],
                )
            )

    ranking = RankingResult(
        run_id=run_id,
        winner_candidate_id=(
            candidate_by_fact_id[winner_fact_id] if winner_fact_id is not None else None
        ),
        ranked_candidate_ids=tuple(candidate_by_fact_id[fact_id] for fact_id in ranked_fact_ids),
    )
    failures = tuple(
        UpstreamFailure(stage=error.stage, code="MAYANK_STAGE_ERROR")
        for error in selection.stage_errors
        if isinstance(error.stage, str) and error.stage.strip()
    )
    if len(failures) != len(selection.stage_errors):
        raise ValueError("Mayank output contains an invalid stage-error record")

    return AdaptedMayankSelection(
        extraction=ExtractionResult(
            run_id=run_id,
            candidate_ids=candidate_ids,
            facts=adapted_facts,
        ),
        ranking=ranking,
        upstream_failures=failures,
        conflicts=tuple(adapted_conflicts),
        no_reference_by_candidate_id=MappingProxyType(no_reference),
    )
