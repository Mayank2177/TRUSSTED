"""Stage 4 perturbation runner; extraction and ranking remain injected upstream stages."""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

from warrant.ids import uuid7
from warrant.integrity.contracts import (
    CandidateObservation,
    ContentKind,
    ExtractionResult,
    Extractor,
    ObservationBlock,
    ProductFact,
    Ranker,
    RankingResult,
    UserIntent,
)


class PerturbationType(StrEnum):
    STRIP_PERSUASION = "strip_persuasion"
    SHUFFLE_ORDER = "shuffle_order"


class StabilityState(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class StabilityConfig:
    shuffle_count: int = 5
    seed: int = 0
    timeout_seconds: float = 30.0
    threshold: float = 1.0

    def __post_init__(self) -> None:
        if type(self.shuffle_count) is not int:
            raise ValueError("shuffle_count must be an integer")
        if self.shuffle_count < 1:
            raise ValueError("shuffle_count must be at least 1")
        if type(self.seed) is not int:
            raise ValueError("seed must be an integer")
        if (
            not isinstance(self.timeout_seconds, (int, float))
            or not isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive")
        if type(self.threshold) not in (int, float) or self.threshold != 1.0:
            raise ValueError("the MVP stability threshold is fixed at strict 100%")


@dataclass(frozen=True, slots=True)
class PerturbationOutcome:
    perturbation: PerturbationType
    run_id: str
    seed: int | None
    winner_candidate_id: str | None
    succeeded: bool
    changed_input: bool
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class StabilityReport:
    run_id: str
    state: StabilityState
    skip_reason: str | None
    baseline_winner_id: str | None
    winner_counts: tuple[tuple[str, int], ...]
    stable: bool
    threshold: float
    planned_count: int
    successful_count: int
    failed_count: int
    changed_count: int
    shuffle_changed_count: int
    outcomes: tuple[PerturbationOutcome, ...]
    winner_flips: tuple[str, ...]
    errors: tuple[str, ...]


class _InvalidResult(ValueError):
    pass


def strip_persuasion(
    observations: tuple[CandidateObservation, ...],
) -> tuple[CandidateObservation, ...]:
    """Remove only blocks explicitly labeled marketing/review; retain unknown content."""
    stripped: list[CandidateObservation] = []
    for item in observations:
        remaining: list[ObservationBlock] = []
        for block in item.blocks:
            if block.kind not in (ContentKind.MARKETING, ContentKind.REVIEW):
                remaining.append(block)
            elif block.structured_data is not None:
                # Preserve structured product fields even if upstream attached them to prose
                # that was classified for removal. The prose itself remains stripped.
                remaining.append(
                    ObservationBlock(ContentKind.STRUCTURED, "", block.structured_data)
                )
        remaining_blocks = tuple(remaining)
        stripped.append(
            CandidateObservation(
                candidate_id=item.candidate_id,
                observation_id=item.observation_id,
                source_uri=item.source_uri,
                content_hash=item.source_content_hash or item.content_hash,
                blocks=remaining_blocks,
                source_content_hash=item.source_content_hash,
            )
        )
    return tuple(stripped)


class StabilityRunner:
    def __init__(
        self,
        extractor: Extractor,
        ranker: Ranker,
        *,
        run_id_factory: Callable[[], str] = uuid7,
    ) -> None:
        self._extractor = extractor
        self._ranker = ranker
        self._run_id_factory = run_id_factory

    @staticmethod
    def skipped(*, run_id: str, reason: str) -> StabilityReport:
        """Represent an intentional cost-control skip separately from missing evidence."""
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be non-empty text")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("skip reason must be non-empty text")
        return StabilityReport(
            run_id=run_id,
            state=StabilityState.SKIPPED,
            skip_reason=reason,
            baseline_winner_id=None,
            winner_counts=(),
            stable=False,
            threshold=1.0,
            planned_count=0,
            successful_count=0,
            failed_count=0,
            changed_count=0,
            shuffle_changed_count=0,
            outcomes=(),
            winner_flips=(),
            errors=(),
        )

    def evaluate(
        self,
        *,
        run_id: str,
        intent: UserIntent,
        observations: tuple[CandidateObservation, ...],
        baseline_extraction: ExtractionResult | None,
        baseline_ranking: RankingResult | None,
        config: StabilityConfig | None = None,
    ) -> StabilityReport:
        config = config or StabilityConfig()
        if not isinstance(run_id, str) or not run_id.strip():
            return self._invalid_report(run_id, None, config, "RUN_ID_INVALID")
        if not isinstance(observations, tuple) or any(
            not isinstance(item, CandidateObservation) for item in observations
        ):
            return self._invalid_report(run_id, None, config, "OBSERVATIONS_INVALID")
        candidate_ids = tuple(item.candidate_id for item in observations)
        if any(
            not isinstance(candidate_id, str) or not candidate_id.strip()
            for candidate_id in candidate_ids
        ):
            return self._invalid_report(run_id, None, config, "CANDIDATE_ID_INVALID")
        if baseline_extraction is None:
            return self._invalid_report(
                run_id, None, config, "BASELINE_EXTRACTION_FAILED_OR_MISSING"
            )
        if baseline_ranking is None:
            return self._invalid_report(run_id, None, config, "BASELINE_RANKING_FAILED_OR_MISSING")
        if not isinstance(baseline_extraction, ExtractionResult) or not isinstance(
            baseline_ranking, RankingResult
        ):
            return self._invalid_report(run_id, None, config, "BASELINE_RESULT_INVALID")
        invalid = self._validate_baseline(
            candidate_ids, baseline_extraction, baseline_ranking, run_id
        )
        if invalid is not None:
            return self._invalid_report(
                run_id, baseline_ranking.winner_candidate_id, config, invalid
            )
        baseline_winner_id = baseline_ranking.winner_candidate_id
        if baseline_winner_id is None:
            return self._invalid_report(run_id, None, config, "BASELINE_WINNER_MISSING")
        baseline_fact = _winner_fact(baseline_extraction.facts, baseline_winner_id)
        if baseline_fact is None or baseline_fact.sku is None:
            return self._invalid_report(
                run_id,
                baseline_ranking.winner_candidate_id,
                config,
                "BASELINE_WINNER_IDENTITY_MISSING",
            )

        stripped = strip_persuasion(observations)
        plans: list[tuple[PerturbationType, int | None, tuple[CandidateObservation, ...], bool]] = [
            (PerturbationType.STRIP_PERSUASION, None, stripped, stripped != observations)
        ]
        for index in range(config.shuffle_count):
            seed = config.seed + index
            shuffled = self._shuffle_order(observations, seed)
            plans.append((PerturbationType.SHUFFLE_ORDER, seed, shuffled, shuffled != observations))

        sub_run_ids: list[str] = []
        seen_run_ids = {run_id}
        try:
            for _ in plans:
                sub_run_id = self._run_id_factory()
                if (
                    not isinstance(sub_run_id, str)
                    or not sub_run_id.strip()
                    or sub_run_id in seen_run_ids
                ):
                    return self._invalid_report(
                        run_id,
                        baseline_ranking.winner_candidate_id,
                        config,
                        "SUB_RUN_ID_INVALID",
                    )
                seen_run_ids.add(sub_run_id)
                sub_run_ids.append(sub_run_id)
        except Exception:
            return self._invalid_report(
                run_id,
                baseline_ranking.winner_candidate_id,
                config,
                "SUB_RUN_ID_GENERATION_FAILED",
            )

        outcomes = tuple(
            self._execute(
                sub_run_id,
                kind,
                seed,
                transformed,
                changed_input,
                intent,
                candidate_ids,
                baseline_fact,
                config.timeout_seconds,
            )
            for sub_run_id, (kind, seed, transformed, changed_input) in zip(
                sub_run_ids, plans, strict=True
            )
        )
        counts = Counter(
            outcome.winner_candidate_id
            for outcome in outcomes
            if outcome.succeeded and outcome.winner_candidate_id is not None
        )
        flips = tuple(
            outcome.run_id
            for outcome in outcomes
            if outcome.succeeded
            and outcome.winner_candidate_id != baseline_ranking.winner_candidate_id
        )
        successful = sum(outcome.succeeded for outcome in outcomes)
        failed = len(outcomes) - successful
        changed_count = sum(outcome.changed_input for outcome in outcomes)
        shuffle_changed_count = sum(
            outcome.changed_input
            for outcome in outcomes
            if outcome.perturbation is PerturbationType.SHUFFLE_ORDER
        )
        stable = (
            baseline_ranking.winner_candidate_id is not None
            and failed == 0
            and successful == len(plans)
            and not flips
        )
        errors = tuple(
            f"{outcome.run_id}:{outcome.error_code}:{outcome.error_message}"
            for outcome in outcomes
            if not outcome.succeeded
        )
        return StabilityReport(
            run_id=run_id,
            state=(StabilityState.COMPLETED if failed == 0 else StabilityState.FAILED),
            skip_reason=None,
            baseline_winner_id=baseline_ranking.winner_candidate_id,
            winner_counts=tuple(sorted(counts.items())),
            stable=stable,
            threshold=config.threshold,
            planned_count=len(plans),
            successful_count=successful,
            failed_count=failed,
            changed_count=changed_count,
            shuffle_changed_count=shuffle_changed_count,
            outcomes=outcomes,
            winner_flips=flips,
            errors=errors,
        )

    def _execute(
        self,
        sub_run_id: str,
        kind: PerturbationType,
        seed: int | None,
        observations: tuple[CandidateObservation, ...],
        changed_input: bool,
        intent: UserIntent,
        expected_candidate_ids: tuple[str, ...],
        baseline_winner_fact: ProductFact,
        timeout_seconds: float,
    ) -> PerturbationOutcome:
        try:
            extraction = self._extractor.extract(
                observations, intent, run_id=sub_run_id, timeout_seconds=timeout_seconds
            )
            if not isinstance(extraction, ExtractionResult):
                raise _InvalidResult("extractor returned an invalid result type")
            if extraction.run_id != sub_run_id:
                raise _InvalidResult("extractor returned the wrong run identifier")
            if not isinstance(extraction.candidate_ids, tuple) or any(
                not isinstance(candidate_id, str) for candidate_id in extraction.candidate_ids
            ):
                raise _InvalidResult("extractor returned invalid candidate identifiers")
            if len(set(extraction.candidate_ids)) != len(extraction.candidate_ids) or set(
                extraction.candidate_ids
            ) != set(expected_candidate_ids):
                raise _InvalidResult("extractor changed candidate identity or membership")
            fact_error = _validate_facts(extraction)
            if fact_error is not None:
                raise _InvalidResult(fact_error)
            ranking = self._ranker.rank(
                extraction, intent, run_id=sub_run_id, timeout_seconds=timeout_seconds
            )
            if not isinstance(ranking, RankingResult) or not isinstance(
                ranking.ranked_candidate_ids, tuple
            ):
                raise _InvalidResult("ranker returned an invalid result type")
            if ranking.run_id != sub_run_id:
                raise _InvalidResult("ranker returned the wrong run identifier")
            winner = ranking.winner_candidate_id
            if winner is None:
                raise _InvalidResult("ranker returned no winner")
            if not isinstance(winner, str):
                raise _InvalidResult("ranker returned an invalid winner identifier")
            if winner not in expected_candidate_ids:
                raise _InvalidResult("ranker selected a candidate outside the input set")
            ranked_ids = ranking.ranked_candidate_ids
            if any(not isinstance(candidate_id, str) for candidate_id in ranked_ids):
                raise _InvalidResult("ranker returned invalid candidate identifiers")
            if len(set(ranked_ids)) != len(ranked_ids):
                raise _InvalidResult("ranker returned duplicate candidate identifiers")
            if winner not in ranked_ids:
                raise _InvalidResult("ranked candidate list does not contain its winner")
            winner_fact = _winner_fact(extraction.facts, winner)
            if winner_fact is None or winner_fact.sku is None:
                raise _InvalidResult("ranked winner has no unique seller/SKU identity")
            if winner == baseline_winner_fact.candidate_id and _purchase_fields(
                winner_fact
            ) != _purchase_fields(baseline_winner_fact):
                return PerturbationOutcome(
                    kind,
                    sub_run_id,
                    seed,
                    None,
                    False,
                    changed_input,
                    "WINNER_FACT_DRIFT",
                    "winning product purchase fields changed",
                )
            return PerturbationOutcome(kind, sub_run_id, seed, winner, True, changed_input)
        except TimeoutError:
            return PerturbationOutcome(
                kind,
                sub_run_id,
                seed,
                None,
                False,
                changed_input,
                "TIMEOUT",
                "upstream stage timed out",
            )
        except Exception as exc:
            code = "INVALID_RESULT" if isinstance(exc, _InvalidResult) else "UPSTREAM_ERROR"
            # Exception text from upstream pages/providers can contain sensitive or untrusted data.
            return PerturbationOutcome(
                kind, sub_run_id, seed, None, False, changed_input, code, type(exc).__name__
            )

    @staticmethod
    def _shuffle_order(
        observations: tuple[CandidateObservation, ...], seed: int
    ) -> tuple[CandidateObservation, ...]:
        """Use the seeded stream until the order changes, if a change is possible."""
        if len(observations) < 2:
            return observations
        generator = random.Random(seed)
        shuffled = list(observations)
        generator.shuffle(shuffled)
        while tuple(shuffled) == observations:
            generator.shuffle(shuffled)
        return tuple(shuffled)

    @staticmethod
    def _validate_baseline(
        candidate_ids: tuple[str, ...],
        extraction: ExtractionResult,
        ranking: RankingResult,
        run_id: str,
    ) -> str | None:
        if not candidate_ids:
            return "EMPTY_CANDIDATE_SET"
        if len(set(candidate_ids)) != len(candidate_ids):
            return "DUPLICATE_CANDIDATE_ID"
        if extraction.run_id != run_id or ranking.run_id != run_id:
            return "BASELINE_RUN_ID_MISMATCH"
        if not isinstance(extraction.candidate_ids, tuple) or not isinstance(
            ranking.ranked_candidate_ids, tuple
        ):
            return "BASELINE_RESULT_INVALID"
        fact_error = _validate_facts(extraction)
        if fact_error is not None:
            return fact_error
        if any(not isinstance(candidate_id, str) for candidate_id in extraction.candidate_ids):
            return "BASELINE_EXTRACTION_CANDIDATE_MISMATCH"
        if len(set(extraction.candidate_ids)) != len(extraction.candidate_ids) or set(
            extraction.candidate_ids
        ) != set(candidate_ids):
            return "BASELINE_EXTRACTION_CANDIDATE_MISMATCH"
        winner = ranking.winner_candidate_id
        if winner is None:
            return "BASELINE_WINNER_MISSING"
        if winner not in candidate_ids:
            return "BASELINE_WINNER_NOT_IN_CANDIDATES"
        ranked_ids = ranking.ranked_candidate_ids
        if any(not isinstance(candidate_id, str) for candidate_id in ranked_ids):
            return "BASELINE_RESULT_INVALID"
        if len(ranked_ids) != len(set(ranked_ids)):
            return "BASELINE_RANKING_DUPLICATE_ID"
        if winner not in ranked_ids or not set(ranked_ids).issubset(candidate_ids):
            return "BASELINE_RANKING_MEMBERSHIP_INVALID"
        winning_facts = [fact for fact in extraction.facts if fact.candidate_id == winner]
        if len(winning_facts) != 1:
            return "BASELINE_WINNER_FACT_INVALID"
        if not winning_facts[0].sku:
            return "BASELINE_WINNER_IDENTITY_MISSING"
        return None

    @staticmethod
    def _invalid_report(
        run_id: str,
        winner_id: str | None,
        config: StabilityConfig,
        error: str,
    ) -> StabilityReport:
        return StabilityReport(
            run_id=run_id,
            state=StabilityState.FAILED,
            skip_reason=None,
            baseline_winner_id=winner_id,
            winner_counts=(),
            stable=False,
            threshold=config.threshold,
            planned_count=0,
            successful_count=0,
            failed_count=0,
            changed_count=0,
            shuffle_changed_count=0,
            outcomes=(),
            winner_flips=(),
            errors=(error,),
        )


def _validate_facts(extraction: ExtractionResult) -> str | None:
    if not isinstance(extraction.facts, tuple):
        return "EXTRACTION_FACTS_INVALID"
    for fact in extraction.facts:
        if not isinstance(fact, ProductFact):
            return "EXTRACTION_FACT_INVALID"
        if fact.candidate_id not in extraction.candidate_ids:
            return "EXTRACTION_FACT_CANDIDATE_MISMATCH"
    return None


def _winner_fact(facts: tuple[ProductFact, ...], candidate_id: str) -> ProductFact | None:
    matching = [fact for fact in facts if fact.candidate_id == candidate_id]
    return matching[0] if len(matching) == 1 else None


def _purchase_fields(fact: ProductFact) -> tuple[object, ...]:
    return (
        fact.seller_id,
        fact.sku,
        fact.gtin,
        fact.price_minor,
        fact.currency,
        fact.shipping_minor,
        fact.additional_charges_minor,
        tuple(sorted(fact.spec.items())),
    )
