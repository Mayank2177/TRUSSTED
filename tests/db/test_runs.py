"""Run history must survive input revisions, failures and repeated submissions."""

from datetime import timedelta
from typing import Literal

import pytest
from sqlalchemy.orm import Session, sessionmaker

from tests.db.conftest import NOW
from warrant.db.contracts.runs import InputReference, RunFinish, RunStart, StageState
from warrant.db.errors import DuplicateRecord, InvalidEvidence, InvalidTransition
from warrant.db.repositories.runs import create_run, finish_run, get_run, record_stage_state
from warrant.db.session import transaction


def start(run_id: str = "run", scenario: str = "attack", repetition: int = 1) -> RunStart:
    return RunStart(
        id=run_id,
        batch_id="batch",
        scenario_id=scenario,
        variant_id="variant",
        repetition=repetition,
        seed=7,
        started_at=NOW,
        intent={"max_price_minor": 10000},
        input_manifest=(
            InputReference(
                role="candidate",
                fixture_id=f"{scenario}-page",
                content_hash="a" * 64,
            ),
        ),
    )


def test_run_lifecycle(factory: sessionmaker[Session], registry: None) -> None:
    with transaction(factory) as session:
        create_run(session, start())
    with transaction(factory) as session:
        current = get_run(session, "run")
        assert current.status == "running"
        assert current.finished_at is None
        record_stage_state(session, "run", StageState(stage="cross_check", state="no_reference"))
        record_stage_state(session, "run", StageState(stage="perturb", state="skipped"))
        finish_run(
            session,
            "run",
            RunFinish(
                status="completed",
                finished_at=NOW + timedelta(seconds=1),
                attacker_success=False,
                latency_ms=1000,
                llm_cost_micro_usd=10,
            ),
        )
    with factory() as session:
        result = get_run(session, "run")
    assert result.attacker_success is False
    assert result.stage_states["perturb"].state == "skipped"
    assert result.input_manifest[0].fixture_id == "attack-page"
    with pytest.raises(InvalidTransition):
        with transaction(factory) as session:
            finish_run(session, "run", RunFinish(status="timeout", finished_at=NOW))


@pytest.mark.parametrize("status", ["error", "timeout"])
def test_failed_runs_remain_without_fabricated_outcomes(
    factory: sessionmaker[Session],
    registry: None,
    status: Literal["error", "timeout"],
) -> None:
    with transaction(factory) as session:
        create_run(session, start())
        finish_run(
            session,
            "run",
            RunFinish(
                status=status,
                finished_at=NOW,
                error_stage="extract",
                error_code="stage_failed",
            ),
        )
    with factory() as session:
        result = get_run(session, "run")
        assert result.status == status
        assert result.attacker_success is None
        assert result.llm_cost_micro_usd is None


def test_duplicate_benchmark_identity_is_rejected(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    with transaction(factory) as session:
        create_run(session, start())
    with pytest.raises(DuplicateRecord):
        with transaction(factory) as session:
            create_run(session, start("another"))


def test_manifest_cannot_point_to_another_scenario(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    value = start().model_copy(
        update={
            "input_manifest": (
                InputReference(
                    role="candidate",
                    fixture_id="benign-page",
                    content_hash="a" * 64,
                ),
            )
        }
    )
    with pytest.raises(InvalidEvidence):
        with transaction(factory) as session:
            create_run(session, value)


def test_completed_outcome_must_match_scenario_kind(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    with transaction(factory) as session:
        create_run(session, start())
    with pytest.raises(InvalidEvidence):
        with transaction(factory) as session:
            finish_run(session, "run", RunFinish(status="completed", finished_at=NOW))
