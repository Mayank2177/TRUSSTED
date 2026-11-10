"""Persist pipeline evidence in the caller's transaction; never calculate rankings."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from trussted.db.contracts.evidence import (
    FactConflictInput,
    ObservationInput,
    ProductFactInput,
    RankingInput,
)
from trussted.db.contracts.runs import Stage, StageState
from trussted.db.errors import InvalidEvidence, InvalidTransition, flush
from trussted.db.repositories.runs import record_stage_state, require_run
from trussted.db.tables.evidence import (
    FactConflictRow,
    ObservationRow,
    ProductFactRow,
    RankingRow,
)
from trussted.db.values import canonical_json, utc_text


def _require_running(session: Session, run_id: str) -> None:
    if require_run(session, run_id).status != "running":
        raise InvalidTransition("Evidence cannot be added to a terminal run")


def _complete_stages(session: Session, run_ids: set[str], stage: Stage) -> None:
    for run_id in sorted(run_ids):
        record_stage_state(session, run_id, StageState(stage=stage, state="completed"))


def save_observations(session: Session, values: Sequence[ObservationInput]) -> tuple[str, ...]:
    """Store metadata without declaring the later extraction stage complete."""
    for value in values:
        _require_running(session, value.run_id)
    session.add_all(
        [
            ObservationRow(**(value.model_dump() | {"fetched_at": utc_text(value.fetched_at)}))
            for value in values
        ]
    )
    flush(session)
    return tuple(value.id for value in values)


def save_product_facts(session: Session, values: Sequence[ProductFactInput]) -> tuple[str, ...]:
    """Save a fact batch and extraction completion, enforcing observation provenance."""
    for value in values:
        _require_running(session, value.run_id)
        observation = session.get(ObservationRow, value.observation_id)
        if observation is None or observation.run_id != value.run_id:
            raise InvalidEvidence("Fact observation must belong to the same run")
    rows = [
        ProductFactRow(
            **(
                value.model_dump()
                | {
                    "spec": canonical_json(value.spec),
                    "source_span": canonical_json(value.source_span.model_dump(mode="json")),
                }
            )
        )
        for value in values
    ]
    _complete_stages(session, {value.run_id for value in values}, "extract")
    session.add_all(rows)
    flush(session)
    return tuple(value.id for value in values)


def save_fact_conflicts(session: Session, values: Sequence[FactConflictInput]) -> tuple[str, ...]:
    """Persist supplied conflicts and cross-check completion; an empty batch records no state."""
    run_ids: set[str] = set()
    for value in values:
        fact = session.get(ProductFactRow, value.fact_id)
        if fact is None:
            raise InvalidEvidence("Conflict fact does not exist")
        _require_running(session, fact.run_id)
        run_ids.add(fact.run_id)
    rows = [
        FactConflictRow(
            **(
                value.model_dump()
                | {
                    "extracted_value": canonical_json(value.extracted_value),
                    "reference_value": canonical_json(value.reference_value),
                }
            )
        )
        for value in values
    ]
    _complete_stages(session, run_ids, "cross_check")
    session.add_all(rows)
    flush(session)
    return tuple(value.id for value in values)


def save_ranking(session: Session, value: RankingInput) -> str:
    """Store one base or perturbed ranking with candidates restricted to its run."""
    _require_running(session, value.run_id)
    for fact_id in value.ordered_fact_ids:
        fact = session.get(ProductFactRow, fact_id)
        if fact is None or fact.run_id != value.run_id:
            raise InvalidEvidence("Ranking candidates must belong to the same run")
    row = RankingRow(
        **(
            value.model_dump()
            | {
                "ordered_fact_ids": canonical_json(list(value.ordered_fact_ids)),
                "scores": canonical_json(dict(value.scores)),
            }
        )
    )
    if value.perturbation == "none":
        _complete_stages(session, {value.run_id}, "rank")
    session.add(row)
    flush(session)
    return value.id
