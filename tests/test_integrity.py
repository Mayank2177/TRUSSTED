from __future__ import annotations

import random
from dataclasses import dataclass

import pytest

from warrant.integrity.contracts import (
    CandidateObservation,
    ContentKind,
    ExtractionResult,
    ObservationBlock,
    ProductFact,
    RankingResult,
    UserIntent,
)
from warrant.integrity.engine import (
    StabilityConfig,
    StabilityRunner,
    StabilityState,
    strip_persuasion,
)

INTENT = UserIntent(800_000, "INR", {"capacity": "1TB"}, None, {"price": 1})


def observation(
    candidate_id: str, *, promo: str | None = None, score: int = 1
) -> CandidateObservation:
    blocks = [
        ObservationBlock(ContentKind.STRUCTURED, "", {"score": score, "capacity": "1TB"}),
        ObservationBlock(ContentKind.FACT, "1 TB SSD for ₹7,500"),
        ObservationBlock(ContentKind.UNCLASSIFIED, "Supports NVMe"),
    ]
    if promo:
        blocks.append(ObservationBlock(ContentKind.MARKETING, promo))
    blocks.append(ObservationBlock(ContentKind.REVIEW, "Fast delivery"))
    return CandidateObservation(
        candidate_id, f"obs-{candidate_id}", "fixture://ssd", "a" * 64, tuple(blocks)
    )


class FixtureExtractor:
    def __init__(self) -> None:
        self.seen: list[tuple[str, ...]] = []
        self.fail_on_marketing = False
        self.timeout = False

    def extract(self, observations, intent, *, run_id, timeout_seconds):
        if self.timeout:
            raise TimeoutError("private page data must not leak to report")
        if self.fail_on_marketing and all(
            block.kind is not ContentKind.MARKETING
            for item in observations
            for block in item.blocks
        ):
            raise RuntimeError("untrusted page body must not leak")
        ids = tuple(item.candidate_id for item in observations)
        self.seen.append(ids)
        facts = tuple(
            ProductFact(
                candidate_id,
                candidate_id,
                7_500,
                "INR",
                "merchant-a",
                {"capacity": "1TB"},
                sku=f"sku-{candidate_id}",
            )
            for candidate_id in ids
        )
        return ExtractionResult(run_id, ids, facts)


@dataclass
class StableRanker:
    calls: int = 0

    def rank(self, extraction, intent, *, run_id, timeout_seconds):
        self.calls += 1
        ranked = tuple(sorted(extraction.candidate_ids))
        return RankingResult(run_id, "ssd-a", ranked)


class FirstPositionRanker:
    def rank(self, extraction, intent, *, run_id, timeout_seconds):
        ids = extraction.candidate_ids
        return RankingResult(run_id, ids[0] if ids else None, ids)


class DriftingExtractor(FixtureExtractor):
    def extract(self, observations, intent, *, run_id, timeout_seconds):
        result = super().extract(
            observations, intent, run_id=run_id, timeout_seconds=timeout_seconds
        )
        facts = tuple(
            ProductFact(
                fact.candidate_id,
                fact.name,
                fact.price_minor + (1 if fact.candidate_id == "ssd-a" else 0),
                fact.currency,
                fact.seller_id,
                fact.spec,
                sku=fact.sku,
            )
            for fact in result.facts
        )
        return ExtractionResult(result.run_id, result.candidate_ids, facts)


class SpecDriftingExtractor(FixtureExtractor):
    def extract(self, observations, intent, *, run_id, timeout_seconds):
        result = super().extract(
            observations, intent, run_id=run_id, timeout_seconds=timeout_seconds
        )
        facts = tuple(
            ProductFact(
                fact.candidate_id,
                fact.name,
                fact.price_minor,
                fact.currency,
                fact.seller_id,
                {**fact.spec, "capacity": "2TB"} if fact.candidate_id == "ssd-a" else fact.spec,
                sku=fact.sku,
            )
            for fact in result.facts
        )
        return ExtractionResult(result.run_id, result.candidate_ids, facts)


def baseline(ids: tuple[str, ...], winner: str | None = "ssd-a"):
    facts = tuple(
        ProductFact(
            candidate_id,
            candidate_id,
            7_500,
            "INR",
            "merchant-a",
            {"capacity": "1TB"},
            sku=f"sku-{candidate_id}",
        )
        for candidate_id in ids
    )
    extraction = ExtractionResult("base", ids, facts)
    ranking = RankingResult("base", winner, ids)
    return extraction, ranking


def test_strip_only_removes_labeled_marketing_and_reviews() -> None:
    original = (observation("ssd-a", promo="Buy now!"),)
    stripped = strip_persuasion(original)
    assert [block.kind for block in stripped[0].blocks] == [
        ContentKind.STRUCTURED,
        ContentKind.FACT,
        ContentKind.UNCLASSIFIED,
    ]
    assert stripped[0].blocks[0].structured_data == {"score": 1, "capacity": "1TB"}
    assert any(block.text == "1 TB SSD for ₹7,500" for block in stripped[0].blocks)
    assert len(original[0].blocks) == 5


@pytest.mark.parametrize("kind", [ContentKind.MARKETING, ContentKind.REVIEW])
def test_stripping_each_persuasion_kind_recomputes_hash(kind: ContentKind) -> None:
    retained = ObservationBlock(ContentKind.FACT, "capacity 1TB")
    removed = ObservationBlock(kind, "limited time")
    original = CandidateObservation(
        "ssd-a", "obs-ssd-a", "fixture://ssd", "a" * 64, (retained, removed)
    )

    stripped = strip_persuasion((original,))[0]

    assert stripped.blocks == (retained,)
    assert stripped.content_hash != original.content_hash
    assert len(stripped.content_hash) == 64


def test_stripping_multiple_blocks_hashes_all_remaining_content_deterministically() -> None:
    source = observation("ssd-a", promo="buy now")
    first = strip_persuasion((source,))[0]
    second = strip_persuasion((source,))[0]

    assert first.content_hash == second.content_hash
    assert first.content_hash != source.content_hash
    assert first.blocks == second.blocks


def test_no_op_stripping_preserves_hash_and_returns_unmodified_content() -> None:
    source = CandidateObservation(
        "ssd-a",
        "obs-ssd-a",
        "fixture://ssd",
        "b" * 64,
        (ObservationBlock(ContentKind.FACT, "1TB"),),
    )

    stripped = strip_persuasion((source,))[0]

    assert stripped.content_hash == source.content_hash
    assert stripped.blocks == source.blocks


def test_stripping_hash_changes_when_remaining_content_changes() -> None:
    first = CandidateObservation(
        "ssd-a",
        "obs-ssd-a",
        "fixture://ssd",
        "a" * 64,
        (ObservationBlock(ContentKind.FACT, "1TB"), ObservationBlock(ContentKind.REVIEW, "good")),
    )
    second = CandidateObservation(
        "ssd-a",
        "obs-ssd-a",
        "fixture://ssd",
        "a" * 64,
        (ObservationBlock(ContentKind.FACT, "2TB"), ObservationBlock(ContentKind.REVIEW, "good")),
    )

    assert strip_persuasion((first,))[0].content_hash != strip_persuasion((second,))[0].content_hash


def test_stripping_preserves_original_observations_and_structured_values() -> None:
    source = observation("ssd-a", promo="buy now")
    source_blocks = source.blocks

    stripped = strip_persuasion((source,))[0]

    assert source.blocks is source_blocks
    assert len(source.blocks) == 5
    assert [block.kind for block in stripped.blocks] == [
        ContentKind.STRUCTURED,
        ContentKind.FACT,
        ContentKind.UNCLASSIFIED,
    ]
    assert stripped.blocks[0].structured_data == {
        "score": 1,
        "capacity": "1TB",
    }


def test_structured_fields_attached_to_removed_prose_are_preserved() -> None:
    marketing = ObservationBlock(
        ContentKind.MARKETING,
        "limited time offer",
        {"sku": "SSD-1TB", "price_minor": 7_500},
    )
    original = CandidateObservation("ssd-a", "obs-ssd-a", "fixture://ssd", "a" * 64, (marketing,))

    stripped = strip_persuasion((original,))[0]

    assert stripped.blocks == (
        ObservationBlock(
            ContentKind.STRUCTURED,
            "",
            {"sku": "SSD-1TB", "price_minor": 7_500},
        ),
    )
    assert stripped.source_content_hash == original.source_content_hash
    assert stripped.content_hash != original.content_hash


def test_baseline_and_transformed_hashes_use_same_typed_content_semantics() -> None:
    blocks = (ObservationBlock(ContentKind.FACT, "SSD 1TB"),)
    first = CandidateObservation("ssd-a", "obs-a", "fixture://ssd", "a" * 64, blocks)
    second = CandidateObservation("ssd-a", "obs-b", "fixture://ssd", "b" * 64, blocks)

    assert first.content_hash == second.content_hash
    assert first.source_content_hash != second.source_content_hash


def test_stripping_last_persuasion_block_hashes_empty_remaining_content() -> None:
    source = CandidateObservation(
        "ssd-a",
        "obs-ssd-a",
        "fixture://ssd",
        "c" * 64,
        (ObservationBlock(ContentKind.MARKETING, "buy now"),),
    )

    stripped = strip_persuasion((source,))[0]

    assert stripped.blocks == ()
    assert stripped.content_hash != source.content_hash
    assert stripped.content_hash == strip_persuasion((source,))[0].content_hash


def test_structured_observation_fields_are_copied_and_immutable() -> None:
    raw_fields = {"capacity": "1TB"}
    block = ObservationBlock(ContentKind.STRUCTURED, "", raw_fields)
    raw_fields["capacity"] = "128GB"
    assert block.structured_data == {"capacity": "1TB"}


def test_stable_winner_requires_every_perturbation_to_succeed() -> None:
    ids = ("ssd-a", "ssd-b", "ssd-c")
    extractor = FixtureExtractor()
    runner = StabilityRunner(
        extractor,
        StableRanker(),
        run_id_factory=iter(["sub-1", "sub-2", "sub-3", "sub-4", "sub-5", "sub-6"]).__next__,
    )
    extraction, ranking = baseline(ids)
    report = runner.evaluate(
        run_id="base",
        intent=INTENT,
        observations=tuple(observation(item) for item in ids),
        baseline_extraction=extraction,
        baseline_ranking=ranking,
        config=StabilityConfig(shuffle_count=5, seed=71),
    )
    assert report.stable is True
    assert report.successful_count == 6
    assert report.failed_count == 0
    assert report.changed_count == 6
    assert report.shuffle_changed_count == 5
    assert all(outcome.changed_input for outcome in report.outcomes)
    assert report.winner_counts == (("ssd-a", 6),)
    assert [outcome.seed for outcome in report.outcomes] == [None, 71, 72, 73, 74, 75]


def test_purchase_relevant_winner_fact_drift_prevents_stability() -> None:
    ids = ("ssd-a", "ssd-b")
    extraction, ranking = baseline(ids)
    report = StabilityRunner(DriftingExtractor(), StableRanker()).evaluate(
        run_id="base",
        intent=INTENT,
        observations=tuple(observation(item) for item in ids),
        baseline_extraction=extraction,
        baseline_ranking=ranking,
        config=StabilityConfig(shuffle_count=1),
    )

    assert report.stable is False
    assert report.successful_count == 0
    assert report.failed_count == 2
    assert all(outcome.error_code == "WINNER_FACT_DRIFT" for outcome in report.outcomes)


def test_decision_relevant_specification_drift_prevents_stability() -> None:
    ids = ("ssd-a", "ssd-b")
    extraction, ranking = baseline(ids)
    report = StabilityRunner(SpecDriftingExtractor(), StableRanker()).evaluate(
        run_id="base",
        intent=INTENT,
        observations=tuple(observation(item) for item in ids),
        baseline_extraction=extraction,
        baseline_ranking=ranking,
        config=StabilityConfig(shuffle_count=1),
    )

    assert report.stable is False
    assert report.successful_count == 0
    assert report.failed_count == 2
    assert all(outcome.error_code == "WINNER_FACT_DRIFT" for outcome in report.outcomes)


def test_winner_without_seller_sku_identity_cannot_be_stable() -> None:
    ids = ("ssd-a",)
    extraction = ExtractionResult(
        "base",
        ids,
        (ProductFact("ssd-a", "SSD", 7_500, "INR", "seller-a", {}),),
    )
    ranking = RankingResult("base", "ssd-a", ids)
    report = StabilityRunner(FixtureExtractor(), StableRanker()).evaluate(
        run_id="base",
        intent=INTENT,
        observations=tuple(observation(item) for item in ids),
        baseline_extraction=extraction,
        baseline_ranking=ranking,
        config=StabilityConfig(shuffle_count=1),
    )

    assert report.stable is False
    assert report.errors == ("BASELINE_WINNER_IDENTITY_MISSING",)


@pytest.mark.parametrize(
    "changes",
    [
        {"price_minor": True},
        {"currency": "inr"},
        {"seller_id": " "},
        {"sku": ""},
        {"shipping_minor": -1},
        {"additional_charges_minor": False},
        {"source_span": (4, 3)},
        {"spec": {"capacity": 1.5}},
    ],
)
def test_product_fact_rejects_malformed_typed_fields(changes: dict[str, object]) -> None:
    fields: dict[str, object] = {
        "candidate_id": "ssd-a",
        "name": "SSD",
        "price_minor": 7_500,
        "currency": "INR",
        "seller_id": "seller-a",
        "spec": {"capacity": "1TB"},
        "sku": "SSD-1TB",
    }
    fields.update(changes)

    with pytest.raises(ValueError):
        ProductFact(**fields)  # type: ignore[arg-type]


def test_position_bias_flips_are_reported_and_unstable() -> None:
    ids = ("ssd-a", "ssd-b", "ssd-c", "ssd-d")
    extractor = FixtureExtractor()
    seen_ids = iter(f"sub-{index}" for index in range(1, 20))
    runner = StabilityRunner(
        extractor, FirstPositionRanker(), run_id_factory=lambda: next(seen_ids)
    )
    extraction, ranking = baseline(ids)
    ranking = RankingResult("base", "ssd-a", ids)
    report = runner.evaluate(
        run_id="base",
        intent=INTENT,
        observations=tuple(observation(item) for item in ids),
        baseline_extraction=extraction,
        baseline_ranking=ranking,
        config=StabilityConfig(shuffle_count=5, seed=3),
    )
    assert report.stable is False
    assert report.winner_flips
    assert report.successful_count == 6


def test_seed_reproduces_order_and_original_input_is_immutable() -> None:
    ids = ("ssd-a", "ssd-b", "ssd-c", "ssd-d")
    source = tuple(observation(item, promo="new stock") for item in ids)
    extraction, ranking = baseline(ids)
    orders: list[list[tuple[str, ...]]] = []
    for _ in range(2):
        extractor = FixtureExtractor()
        sub_ids = iter(f"sub-{index}" for index in range(6))
        runner = StabilityRunner(
            extractor,
            StableRanker(),
            run_id_factory=lambda ids=sub_ids: next(ids),
        )
        runner.evaluate(
            run_id="base",
            intent=INTENT,
            observations=source,
            baseline_extraction=extraction,
            baseline_ranking=ranking,
            config=StabilityConfig(shuffle_count=5, seed=17),
        )
        orders.append(extractor.seen)
    assert orders[0] == orders[1]
    assert tuple(item.candidate_id for item in source) == ids
    assert all(len(item.blocks) == 5 for item in source)


def test_duplicate_subrun_ids_fail_closed_before_upstream_callbacks() -> None:
    extractor = FixtureExtractor()
    extraction, ranking = baseline(("ssd-a", "ssd-b"))
    report = StabilityRunner(
        extractor, StableRanker(), run_id_factory=lambda: "same-subrun"
    ).evaluate(
        run_id="base",
        intent=INTENT,
        observations=(observation("ssd-a"), observation("ssd-b")),
        baseline_extraction=extraction,
        baseline_ranking=ranking,
        config=StabilityConfig(shuffle_count=2),
    )

    assert report.stable is False
    assert report.errors == ("SUB_RUN_ID_INVALID",)
    assert extractor.seen == []


def test_deliberately_skipped_stability_is_distinct_from_missing_baseline() -> None:
    skipped = StabilityRunner.skipped(run_id="parent-run", reason="below_cost_threshold")
    missing = StabilityRunner(FixtureExtractor(), StableRanker()).evaluate(
        run_id="parent-run",
        intent=INTENT,
        observations=(observation("ssd-a"),),
        baseline_extraction=None,
        baseline_ranking=None,
    )

    assert skipped.state is StabilityState.SKIPPED
    assert skipped.skip_reason == "below_cost_threshold"
    assert skipped.stable is False
    assert skipped.planned_count == 0
    assert skipped.failed_count == 0
    assert skipped.errors == ()
    assert missing.state is StabilityState.FAILED
    assert missing.errors == ("BASELINE_EXTRACTION_FAILED_OR_MISSING",)


def test_identity_shuffle_is_redrawn_deterministically() -> None:
    ids = ("ssd-a", "ssd-b", "ssd-c")
    source = tuple(observation(item) for item in ids)
    identity_seed = None
    for seed in range(100):
        candidate = list(source)
        random.Random(seed).shuffle(candidate)
        if tuple(candidate) == source:
            identity_seed = seed
            break
    assert identity_seed is not None

    orders: list[tuple[str, ...]] = []
    for _ in range(2):
        extractor = FixtureExtractor()
        extraction, ranking = baseline(ids)
        StabilityRunner(extractor, StableRanker()).evaluate(
            run_id="base",
            intent=INTENT,
            observations=source,
            baseline_extraction=extraction,
            baseline_ranking=ranking,
            config=StabilityConfig(shuffle_count=1, seed=identity_seed),
        )
        orders.append(extractor.seen[1])

    assert orders[0] == orders[1]
    assert orders[0] != ids
    assert (
        len(
            {
                tuple(item.candidate_id for item in StabilityRunner._shuffle_order(source, seed))
                for seed in range(8)
            }
        )
        > 1
    )


def test_single_candidate_reports_unchanged_shuffle_without_faking_instability() -> None:
    ids = ("ssd-a",)
    source = tuple(observation(item) for item in ids)
    extraction, ranking = baseline(ids)
    report = StabilityRunner(FixtureExtractor(), StableRanker()).evaluate(
        run_id="base",
        intent=INTENT,
        observations=source,
        baseline_extraction=extraction,
        baseline_ranking=ranking,
        config=StabilityConfig(shuffle_count=3, seed=5),
    )

    assert report.stable is True
    assert report.planned_count == 4
    assert report.changed_count == 1  # persuasion block removal only
    assert report.shuffle_changed_count == 0
    assert [outcome.changed_input for outcome in report.outcomes] == [True, False, False, False]


def test_no_op_strip_and_single_candidate_have_zero_changed_counts() -> None:
    source = CandidateObservation(
        "ssd-a",
        "obs-ssd-a",
        "fixture://ssd",
        "d" * 64,
        (ObservationBlock(ContentKind.FACT, "1TB"),),
    )
    extraction, ranking = baseline(("ssd-a",))
    report = StabilityRunner(FixtureExtractor(), StableRanker()).evaluate(
        run_id="base",
        intent=INTENT,
        observations=(source,),
        baseline_extraction=extraction,
        baseline_ranking=ranking,
        config=StabilityConfig(shuffle_count=2),
    )

    assert report.stable is True
    assert report.changed_count == 0
    assert report.shuffle_changed_count == 0
    assert all(not outcome.changed_input for outcome in report.outcomes)


def test_partial_extraction_failure_is_visible_and_prevents_stability() -> None:
    ids = ("ssd-a", "ssd-b")
    extractor = FixtureExtractor()
    extractor.fail_on_marketing = True
    extraction, ranking = baseline(ids)
    report = StabilityRunner(extractor, StableRanker()).evaluate(
        run_id="base",
        intent=INTENT,
        observations=tuple(observation(i, promo="offer") for i in ids),
        baseline_extraction=extraction,
        baseline_ranking=ranking,
        config=StabilityConfig(shuffle_count=1, seed=1),
    )
    assert report.failed_count == 1
    assert report.stable is False
    assert report.outcomes[0].error_code == "UPSTREAM_ERROR"
    assert report.outcomes[0].changed_input is True
    assert report.changed_count == 2
    assert report.shuffle_changed_count == 1
    assert "untrusted page body" not in " ".join(report.errors)


def test_timeout_and_ranking_error_are_visible() -> None:
    ids = ("ssd-a", "ssd-b")
    extraction, ranking = baseline(ids)
    extractor = FixtureExtractor()
    extractor.timeout = True
    timed = StabilityRunner(extractor, StableRanker()).evaluate(
        run_id="base",
        intent=INTENT,
        observations=tuple(observation(i) for i in ids),
        baseline_extraction=extraction,
        baseline_ranking=ranking,
        config=StabilityConfig(shuffle_count=1),
    )
    assert timed.outcomes[0].error_code == "TIMEOUT"
    assert not timed.stable

    class BrokenRanker:
        def rank(self, *args, **kwargs):
            raise RuntimeError("ranking provider secret")

    failed = StabilityRunner(FixtureExtractor(), BrokenRanker()).evaluate(
        run_id="base",
        intent=INTENT,
        observations=tuple(observation(i) for i in ids),
        baseline_extraction=extraction,
        baseline_ranking=ranking,
        config=StabilityConfig(shuffle_count=1),
    )
    assert failed.outcomes[0].error_code == "UPSTREAM_ERROR"
    assert "ranking provider secret" not in " ".join(failed.errors)


def test_missing_and_invalid_baselines_fail_closed_without_calls() -> None:
    runner = StabilityRunner(FixtureExtractor(), StableRanker())
    empty, empty_rank = baseline((), None)
    report = runner.evaluate(
        run_id="base",
        intent=INTENT,
        observations=(),
        baseline_extraction=empty,
        baseline_ranking=empty_rank,
        config=StabilityConfig(shuffle_count=1),
    )
    assert not report.stable and report.failed_count == 0
    assert report.planned_count == 0
    assert report.errors == ("EMPTY_CANDIDATE_SET",)
    assert report.changed_count == 0
    assert report.shuffle_changed_count == 0

    ids = ("ssd-a", "ssd-b")
    extraction, ranking = baseline(ids, None)
    missing = runner.evaluate(
        run_id="base",
        intent=INTENT,
        observations=tuple(observation(i) for i in ids),
        baseline_extraction=extraction,
        baseline_ranking=ranking,
    )
    assert missing.errors == ("BASELINE_WINNER_MISSING",)


def test_baseline_extraction_or_ranking_failure_is_reported() -> None:
    ids = ("ssd-a", "ssd-b")
    observations = tuple(observation(item) for item in ids)
    extraction, ranking = baseline(ids)
    runner = StabilityRunner(FixtureExtractor(), StableRanker())
    extraction_failed = runner.evaluate(
        run_id="base",
        intent=INTENT,
        observations=observations,
        baseline_extraction=None,
        baseline_ranking=ranking,
    )
    ranking_failed = runner.evaluate(
        run_id="base",
        intent=INTENT,
        observations=observations,
        baseline_extraction=extraction,
        baseline_ranking=None,
    )
    assert extraction_failed.errors == ("BASELINE_EXTRACTION_FAILED_OR_MISSING",)
    assert ranking_failed.errors == ("BASELINE_RANKING_FAILED_OR_MISSING",)
    assert not extraction_failed.stable and not ranking_failed.stable


def test_duplicate_candidate_ids_are_rejected() -> None:
    ids = ("ssd-a", "ssd-a")
    extraction, ranking = baseline(ids)
    report = StabilityRunner(FixtureExtractor(), StableRanker()).evaluate(
        run_id="base",
        intent=INTENT,
        observations=tuple(observation(i) for i in ids),
        baseline_extraction=extraction,
        baseline_ranking=ranking,
    )
    assert report.errors == ("DUPLICATE_CANDIDATE_ID",)
    assert report.failed_count == 0
    assert report.planned_count == 0


def test_extraction_that_drops_a_candidate_is_rejected() -> None:
    class DropsCandidate(FixtureExtractor):
        def extract(self, observations, intent, *, run_id, timeout_seconds):
            return ExtractionResult(run_id, ("ssd-a",), ())

    ids = ("ssd-a", "ssd-b")
    extraction, ranking = baseline(ids)
    report = StabilityRunner(DropsCandidate(), StableRanker()).evaluate(
        run_id="base",
        intent=INTENT,
        observations=tuple(observation(i) for i in ids),
        baseline_extraction=extraction,
        baseline_ranking=ranking,
        config=StabilityConfig(shuffle_count=1),
    )
    assert report.outcomes[0].error_code == "INVALID_RESULT"
    assert report.stable is False


def test_baseline_ranking_must_contain_its_winner() -> None:
    ids = ("ssd-a", "ssd-b")
    extraction, _ = baseline(ids)
    ranking = RankingResult("base", "ssd-a", ("ssd-b",))
    report = StabilityRunner(FixtureExtractor(), StableRanker()).evaluate(
        run_id="base",
        intent=INTENT,
        observations=tuple(observation(i) for i in ids),
        baseline_extraction=extraction,
        baseline_ranking=ranking,
        config=StabilityConfig(shuffle_count=1),
    )
    assert report.errors == ("BASELINE_RANKING_MEMBERSHIP_INVALID",)


def test_stability_config_rejects_non_finite_or_non_integer_values() -> None:
    import math

    import pytest

    with pytest.raises(ValueError):
        StabilityConfig(shuffle_count=True)
    with pytest.raises(ValueError):
        StabilityConfig(timeout_seconds=math.nan)
    with pytest.raises(ValueError):
        StabilityConfig(seed=1.5)  # type: ignore[arg-type]


@pytest.mark.parametrize("shuffle_count", [0, -1, -5])
def test_stability_config_requires_at_least_one_shuffle(shuffle_count: int) -> None:
    with pytest.raises(ValueError, match="shuffle_count must be at least 1"):
        StabilityConfig(shuffle_count=shuffle_count)


@pytest.mark.parametrize("shuffle_count", [1, 2, 8])
def test_stability_config_accepts_positive_shuffle_counts(shuffle_count: int) -> None:
    assert StabilityConfig(shuffle_count=shuffle_count).shuffle_count == shuffle_count


def test_stability_config_preserves_default_shuffle_count() -> None:
    assert StabilityConfig().shuffle_count == 5
