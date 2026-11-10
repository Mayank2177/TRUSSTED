"""Evidence persistence must preserve provenance and reject mixed-run evidence."""

import json
from collections.abc import Callable

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from tests.db.conftest import NOW
from tests.db.test_runs import start
from trussted.db.contracts.evidence import (
    FactConflictInput,
    ObservationInput,
    ProductFactInput,
    RankingInput,
    SourceSpan,
)
from trussted.db.contracts.runs import RunFinish, StageState
from trussted.db.errors import DuplicateRecord, InvalidEvidence, InvalidTransition
from trussted.db.repositories.evidence import (
    save_fact_conflicts,
    save_observations,
    save_product_facts,
    save_ranking,
)
from trussted.db.repositories.runs import create_run, finish_run, get_run, record_stage_state
from trussted.db.session import transaction
from trussted.db.tables.evidence import (
    FactConflictRow,
    ObservationRow,
    ProductFactRow,
    RankingRow,
)


def observation(identifier: str = "observation", run_id: str = "run") -> ObservationInput:
    return ObservationInput(
        id=identifier,
        run_id=run_id,
        url="https://shop.example/product",
        content_hash="b" * 64,
        byte_size=100,
        fetched_at=NOW,
    )


def fact(identifier: str = "fact", run_id: str = "run") -> ProductFactInput:
    return ProductFactInput(
        id=identifier,
        run_id=run_id,
        observation_id="observation",
        sku="SKU-7",
        name="Widget",
        price_minor=1250,
        currency="USD",
        spec={"weight": {"value": 2, "unit": "kg"}},
        seller_id="seller",
        source_span=SourceSpan(start=2, end=20),
    )


def ranking(perturbation: str = "none", identifier: str = "ranking") -> RankingInput:
    return RankingInput(
        id=identifier,
        run_id="run",
        perturbation=perturbation,
        ordered_fact_ids=("fact",),
        scores={"fact": 0.9},
        winner_fact_id="fact",
    )


def prepare(session: Session, *, other_run: bool = False) -> None:
    create_run(session, start())
    if other_run:
        create_run(session, start("other", repetition=2))
    save_observations(session, (observation(),))
    save_product_facts(session, (fact(),))


def test_evidence_round_trip(factory: sessionmaker[Session], registry: None) -> None:
    with transaction(factory) as session:
        prepare(session)
        save_fact_conflicts(
            session,
            (
                FactConflictInput(
                    id="conflict",
                    fact_id="fact",
                    field="weight",
                    extracted_value=2,
                    reference_value=3,
                    severity="high",
                    reference_source="reference-v1",
                ),
            ),
        )
        for index, perturbation in enumerate(
            ("none", "strip_persuasion", "shuffle_0", "shuffle_1")
        ):
            save_ranking(session, ranking(perturbation, f"ranking-{index}"))
    with factory() as session:
        stored = session.get(ProductFactRow, "fact")
        assert stored is not None
        assert stored.sku == "SKU-7"
        assert stored.price_minor == 1250
        assert json.loads(stored.source_span) == {"start": 2, "end": 20}
        assert json.loads(stored.spec) == {"weight": {"value": 2, "unit": "kg"}}
        observed = session.get(ObservationRow, "observation")
        assert observed is not None and observed.fetched_at == "2026-01-01T00:00:00.000000Z"
        conflict = session.get(FactConflictRow, "conflict")
        assert conflict is not None and json.loads(conflict.reference_value) == 3
        rows = session.scalars(select(RankingRow)).all()
        assert len(rows) == 4
        assert all(json.loads(row.ordered_fact_ids) == ["fact"] for row in rows)
        assert get_run(session, "run").stage_states["extract"].state == "completed"
        assert get_run(session, "run").stage_states["cross_check"].state == "completed"


def test_fact_cannot_use_other_runs_observation(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    with transaction(factory) as session:
        prepare(session, other_run=True)
    with pytest.raises(InvalidEvidence), transaction(factory) as session:
        save_product_facts(session, (fact("cross", "other"),))


def test_database_enforces_same_run_observation(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    with transaction(factory) as session:
        prepare(session, other_run=True)
    with pytest.raises(InvalidEvidence), transaction(factory) as session:
        session.execute(
            text("""
            INSERT INTO product_facts
            (id,run_id,observation_id,sku,name,price_minor,currency,spec,seller_id,source_span)
            VALUES ('cross','other','observation','sku','name',1,'USD','{}','seller','{}')
        """)
        )


def test_ranking_cannot_include_other_runs_fact(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    with transaction(factory) as session:
        prepare(session, other_run=True)
    with pytest.raises(InvalidEvidence), transaction(factory) as session:
        save_ranking(session, ranking().model_copy(update={"run_id": "other"}))


def test_ranking_winner_must_be_candidate() -> None:
    with pytest.raises(ValidationError):
        RankingInput(
            id="rank",
            run_id="run",
            perturbation="none",
            ordered_fact_ids=("fact",),
            scores={"fact": 1},
            winner_fact_id="unranked",
        )


def test_duplicate_candidates_rejected() -> None:
    with pytest.raises(ValidationError):
        RankingInput(
            id="rank",
            run_id="run",
            perturbation="none",
            ordered_fact_ids=("fact", "fact"),
            scores={"fact": 1},
            winner_fact_id="fact",
        )


def test_empty_ranking_has_null_winner(factory: sessionmaker[Session], registry: None) -> None:
    with transaction(factory) as session:
        create_run(session, start())
        save_ranking(
            session,
            RankingInput(
                id="rank",
                run_id="run",
                perturbation="none",
                ordered_fact_ids=(),
                scores={},
            ),
        )
    with factory() as session:
        stored = session.get(RankingRow, "rank")
        assert stored is not None and stored.winner_fact_id is None


def test_bulk_save_rolls_back(factory: sessionmaker[Session], registry: None) -> None:
    with transaction(factory) as session:
        create_run(session, start())
    with pytest.raises(DuplicateRecord), transaction(factory) as session:
        save_observations(session, (observation(), observation()))
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(ObservationRow)) == 0


@pytest.mark.parametrize("stage", ["extract", "cross_check"])
def test_bulk_stage_failure_rolls_back_rows_and_state(
    factory: sessionmaker[Session],
    registry: None,
    stage: str,
) -> None:
    with transaction(factory) as session:
        if stage == "extract":
            create_run(session, start())
            save_observations(session, (observation(),))
        else:
            prepare(session)
    with pytest.raises(DuplicateRecord), transaction(factory) as session:
        if stage == "extract":
            save_product_facts(session, (fact(), fact()))
        else:
            value = FactConflictInput(
                id="conflict",
                fact_id="fact",
                field="price",
                extracted_value=1,
                reference_value=2,
                severity="low",
                reference_source="reference",
            )
            save_fact_conflicts(session, (value, value))
    with factory() as session:
        table = ProductFactRow if stage == "extract" else FactConflictRow
        assert session.scalar(select(func.count()).select_from(table)) == 0
        assert stage not in get_run(session, "run").stage_states


def test_ranking_preserves_candidate_order(factory: sessionmaker[Session], registry: None) -> None:
    with transaction(factory) as session:
        prepare(session)
        save_product_facts(session, (fact("second-fact"),))
        save_ranking(
            session,
            RankingInput(
                id="rank",
                run_id="run",
                perturbation="none",
                ordered_fact_ids=("second-fact", "fact"),
                scores={"fact": 0.5, "second-fact": 0.8},
                winner_fact_id="second-fact",
            ),
        )
    with factory() as session:
        row = session.get(RankingRow, "rank")
        assert row is not None and row.winner_fact_id == "second-fact"
        assert json.loads(row.ordered_fact_ids) == ["second-fact", "fact"]
        assert json.loads(row.scores) == {"fact": 0.5, "second-fact": 0.8}


def test_empty_bulk_does_not_replace_missing_reference(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    with transaction(factory) as session:
        create_run(session, start())
        record_stage_state(session, "run", StageState(stage="cross_check", state="no_reference"))
        assert save_fact_conflicts(session, ()) == ()
        assert save_observations(session, ()) == ()
        assert save_product_facts(session, ()) == ()
        assert get_run(session, "run").stage_states["cross_check"].state == "no_reference"


def test_conflict_requires_persisted_fact(factory: sessionmaker[Session], registry: None) -> None:
    with transaction(factory) as session:
        create_run(session, start())
    value = FactConflictInput(
        id="conflict",
        fact_id="missing",
        field="price",
        extracted_value=1,
        reference_value=2,
        severity="low",
        reference_source="reference",
    )
    with pytest.raises(InvalidEvidence), transaction(factory) as session:
        save_fact_conflicts(session, (value,))


@pytest.mark.parametrize("offsets", [(True, 2), (-1, 2), (4, 3), (1.0, 2)])
def test_invalid_source_span(offsets: tuple[object, object]) -> None:
    with pytest.raises(ValidationError):
        SourceSpan.model_validate({"start": offsets[0], "end": offsets[1]})


@pytest.mark.parametrize(
    "changes",
    [
        {"price_minor": 1.5},
        {"price_minor": True},
        {"price_minor": -1},
        {"currency": "usd"},
        {"currency": "US"},
        {"spec": {"weight": float("nan")}},
    ],
)
def test_invalid_fact_values(changes: dict[str, object]) -> None:
    with pytest.raises((ValidationError, ValueError)):
        ProductFactInput.model_validate(fact().model_dump() | changes)


@pytest.mark.parametrize("score", [float("inf"), float("nan"), True, "0.5"])
def test_ranking_rejects_nonfinite_or_coerced_score(score: object) -> None:
    with pytest.raises(ValidationError):
        RankingInput.model_validate(ranking().model_dump() | {"scores": {"fact": score}})


@pytest.mark.parametrize(
    "changes",
    [
        {"scores": {"unranked": 0.5}},
        {"perturbation": "shuffle_x"},
        {"ordered_fact_ids": (), "scores": {}, "winner_fact_id": "fact"},
    ],
)
def test_ranking_rejects_inconsistent_candidates(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        RankingInput.model_validate(ranking().model_dump() | changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"byte_size": True},
        {"byte_size": -1},
        {"byte_size": 1.5},
        {"content_hash": "A" * 64},
        {"fetched_at": "2026-01-01T00:00:00"},
    ],
)
def test_observation_rejects_invalid_metadata(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ObservationInput.model_validate(observation().model_dump() | changes)


def test_stage_failure_rolls_back_evidence(factory: sessionmaker[Session], registry: None) -> None:
    with transaction(factory) as session:
        create_run(session, start())
        save_observations(session, (observation(),))
        record_stage_state(session, "run", StageState(stage="extract", state="error"))
    with pytest.raises(InvalidTransition), transaction(factory) as session:
        save_product_facts(session, (fact(),))
    with factory() as session:
        assert session.get(ProductFactRow, "fact") is None
        assert get_run(session, "run").stage_states["extract"].state == "error"


@pytest.mark.parametrize("save", ["observations", "facts", "conflicts", "ranking"])
def test_evidence_rejected_after_run_finishes(
    factory: sessionmaker[Session],
    registry: None,
    save: str,
) -> None:
    with transaction(factory) as session:
        prepare(session)
        finish_run(session, "run", RunFinish(status="timeout", finished_at=NOW))
    operations: dict[str, Callable[[Session], object]] = {
        "observations": lambda session: save_observations(session, (observation("new"),)),
        "facts": lambda session: save_product_facts(session, (fact("new"),)),
        "conflicts": lambda session: save_fact_conflicts(
            session,
            (
                FactConflictInput(
                    id="new",
                    fact_id="fact",
                    field="price",
                    extracted_value=1,
                    reference_value=2,
                    severity="low",
                    reference_source="reference",
                ),
            ),
        ),
        "ranking": lambda session: save_ranking(session, ranking()),
    }
    with pytest.raises(InvalidTransition), transaction(factory) as session:
        operations[save](session)
