"""Run repositories; policy and outcome labeling remain caller responsibilities."""

import json
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from trussted.db.contracts.runs import RunFinish, RunRecord, RunStart, StageState
from trussted.db.errors import (
    InvalidEvidence,
    InvalidTransition,
    RecordNotFound,
    flush,
    storage_errors,
)
from trussted.db.tables.registry import FixtureRow, ScenarioRow
from trussted.db.tables.runs import RunRow
from trussted.db.values import canonical_json, utc_text


def require_run(session: Session, run_id: str) -> RunRow:
    """Find a run or raise a typed missing-record error."""
    row = session.get(RunRow, run_id)
    if row is None:
        raise RecordNotFound("Run does not exist")
    return row


def create_run(session: Session, value: RunStart) -> str:
    """Persist a running attempt and pin its exact scenario fixture inputs."""
    scenario = session.get(ScenarioRow, value.scenario_id)
    if scenario is None:
        raise InvalidEvidence("Unknown scenario revision")
    for item in value.input_manifest:
        fixture = session.get(FixtureRow, item.fixture_id)
        if (
            fixture is None
            or fixture.scenario_id != value.scenario_id
            or fixture.content_hash != item.content_hash
        ):
            raise InvalidEvidence("Input manifest does not match this scenario's fixtures")
    session.add(
        RunRow(
            id=value.id,
            batch_id=value.batch_id,
            scenario_id=value.scenario_id,
            variant_id=value.variant_id,
            repetition=value.repetition,
            seed=value.seed,
            status="running",
            started_at=utc_text(value.started_at),
            intent=canonical_json(value.intent),
            stage_states="{}",
            input_manifest=canonical_json(
                [item.model_dump(mode="json") for item in value.input_manifest]
            ),
        )
    )
    flush(session)
    return value.id


def get_run(session: Session, run_id: str) -> RunRecord:
    """Return validated, detached values without leaking ORM state."""
    row = require_run(session, run_id)
    data = {column.name: getattr(row, column.name) for column in RunRow.__table__.columns}
    for name in ("intent", "input_manifest", "stage_states"):
        data[name] = json.loads(data[name])
    return RunRecord.model_validate(data)


def finish_run(session: Session, run_id: str, value: RunFinish) -> None:
    """Finalize an attempt once; retain failed/timeout attempts with NULL outcomes."""
    row = require_run(session, run_id)
    if row.status != "running":
        raise InvalidTransition("A terminal run cannot be overwritten")
    if value.finished_at < datetime.fromisoformat(row.started_at):
        raise InvalidEvidence("Run cannot finish before it starts")
    scenario = session.get(ScenarioRow, row.scenario_id)
    assert scenario is not None
    if value.status == "completed":
        if scenario.kind == "attack":
            valid = value.attacker_success is not None and (
                value.benign_success is None and value.false_block is None
            )
        else:
            valid = value.attacker_success is None and (
                value.benign_success is not None and value.false_block is not None
            )
        if not valid or value.error_code is not None or value.error_stage is not None:
            raise InvalidEvidence("Completed outcome labels must match the scenario kind")
    elif any(
        label is not None
        for label in (
            value.attacker_success,
            value.benign_success,
            value.false_block,
        )
    ):
        raise InvalidEvidence("Failed runs must not fabricate outcome labels")
    fields = value.model_dump()
    fields["finished_at"] = utc_text(value.finished_at)
    with storage_errors():
        changed = session.execute(
            update(RunRow)
            .where(RunRow.id == run_id, RunRow.status == "running")
            .values(**fields)
            .returning(RunRow.id)
        ).scalar_one_or_none()
    if changed is None:
        raise InvalidTransition("A terminal run cannot be overwritten")


def record_stage_state(session: Session, run_id: str, value: StageState) -> None:
    """Save an explicit stage result; repeated identical records are harmless."""
    row = require_run(session, run_id)
    if row.status != "running":
        raise InvalidTransition("A terminal run's stage evidence cannot be overwritten")
    states = json.loads(row.stage_states)
    supplied = value.model_dump(mode="json")
    if value.stage in states and states[value.stage] != supplied:
        raise InvalidTransition("A stage outcome was already recorded")
    states[value.stage] = supplied
    row.stage_states = canonical_json(states)
    flush(session)
