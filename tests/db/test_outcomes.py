"""Outcome records preserve explicit decisions and distinguish skipped checks."""

import json
from typing import Literal

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from tests.db.conftest import NOW
from tests.db.test_evidence import fact, observation, prepare
from tests.db.test_runs import start
from trussted.db.contracts.outcomes import DecisionInput, StabilityInput
from trussted.db.contracts.runs import RunFinish, StageState
from trussted.db.errors import DuplicateRecord, InvalidEvidence, InvalidTransition
from trussted.db.repositories.evidence import save_observations, save_product_facts
from trussted.db.repositories.outcomes import save_decision, save_stability_report
from trussted.db.repositories.runs import create_run, finish_run, get_run, record_stage_state
from trussted.db.session import transaction
from trussted.db.tables.outcomes import DecisionRow, StabilityRow


def stability() -> StabilityInput:
    return StabilityInput(
        id="stability",
        run_id="run",
        winner_counts={"fact": 2},
        stable=True,
        threshold=0.8,
        flips=[{"perturbation": "shuffle_1", "winner_fact_id": "fact"}],
    )


def decision(result: Literal["ALLOW", "STEP_UP", "BLOCK"] = "ALLOW") -> DecisionInput:
    return DecisionInput(
        id="decision",
        run_id="run",
        result=result,
        reasons=("reference_matches",),
        policy_version="policy-1",
        amount_minor=1250,
        currency="USD",
    )


@pytest.mark.parametrize("result", ["ALLOW", "STEP_UP", "BLOCK"])
def test_all_decision_values_round_trip(
    factory: sessionmaker[Session],
    registry: None,
    result: Literal["ALLOW", "STEP_UP", "BLOCK"],
) -> None:
    with transaction(factory) as session:
        create_run(session, start())
        assert save_decision(session, decision(result)) == "decision"
    with factory() as session:
        row = session.get(DecisionRow, "decision")
        assert row is not None and row.result == result
        assert json.loads(row.reasons) == ["reference_matches"]
        assert row.amount_minor == 1250 and row.currency == "USD"
        assert get_run(session, "run").stage_states["decide"].state == "completed"


def test_duplicate_decision_rejected(factory: sessionmaker[Session], registry: None) -> None:
    with transaction(factory) as session:
        create_run(session, start())
        save_decision(session, decision())
    with pytest.raises(DuplicateRecord), transaction(factory) as session:
        save_decision(session, decision("BLOCK").model_copy(update={"id": "another"}))
    with factory() as session:
        row = session.get(DecisionRow, "decision")
        assert row is not None and row.result == "ALLOW"


def test_stability_round_trip(factory: sessionmaker[Session], registry: None) -> None:
    with transaction(factory) as session:
        prepare(session)
        save_stability_report(session, stability())
    with factory() as session:
        row = session.get(StabilityRow, "stability")
        assert row is not None and row.stable is True
        assert json.loads(row.winner_counts) == {"fact": 2}
        assert json.loads(row.flips) == [{"perturbation": "shuffle_1", "winner_fact_id": "fact"}]
        assert get_run(session, "run").stage_states["perturb"].state == "completed"


def test_duplicate_stability_rejected(factory: sessionmaker[Session], registry: None) -> None:
    with transaction(factory) as session:
        prepare(session)
        save_stability_report(session, stability())
    with pytest.raises(DuplicateRecord), transaction(factory) as session:
        save_stability_report(session, stability().model_copy(update={"id": "another"}))


@pytest.mark.parametrize("state", ["skipped", "error", "timeout"])
def test_missing_and_skipped_are_not_stable(
    factory: sessionmaker[Session],
    registry: None,
    state: str,
) -> None:
    with transaction(factory) as session:
        create_run(session, start())
        assert "perturb" not in get_run(session, "run").stage_states
        record_stage_state(session, "run", StageState(stage="cross_check", state="no_reference"))
        record_stage_state(
            session,
            "run",
            StageState.model_validate(
                {
                    "stage": "perturb",
                    "state": state,
                    "reason_code": "unavailable",
                }
            ),
        )
    with factory() as session:
        assert session.get(StabilityRow, "stability") is None
        assert get_run(session, "run").stage_states["perturb"].state == state
        assert get_run(session, "run").stage_states["cross_check"].state == "no_reference"


@pytest.mark.parametrize("identity", ["unknown", "other-fact"])
def test_stability_requires_current_run_fact_ids(
    factory: sessionmaker[Session],
    registry: None,
    identity: str,
) -> None:
    with transaction(factory) as session:
        prepare(session, other_run=True)
        save_observations(session, (observation("other-observation", "other"),))
        save_product_facts(
            session,
            (
                fact("other-fact", "other").model_copy(
                    update={
                        "observation_id": "other-observation",
                    }
                ),
            ),
        )
    with pytest.raises(InvalidEvidence), transaction(factory) as session:
        save_stability_report(
            session, stability().model_copy(update={"winner_counts": {identity: 2}})
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"stable": 1},
        {"threshold": -0.1},
        {"threshold": 1.1},
        {"threshold": float("nan")},
        {"threshold": float("inf")},
        {"winner_counts": {"fact": -1}},
        {"winner_counts": {"fact": True}},
        {"flips": [{"score": float("inf")}]},
    ],
)
def test_stability_validation(changes: dict[str, object]) -> None:
    with pytest.raises((ValidationError, ValueError)):
        StabilityInput.model_validate(stability().model_dump() | changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"amount_minor": 1.5},
        {"amount_minor": True},
        {"amount_minor": -1},
        {"currency": "usd"},
        {"result": "allow"},
    ],
)
def test_decision_validation(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DecisionInput.model_validate(decision().model_dump() | changes)


def test_stability_and_stage_update_are_atomic(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    with transaction(factory) as session:
        prepare(session)
        record_stage_state(session, "run", StageState(stage="perturb", state="skipped"))
    with pytest.raises(InvalidTransition), transaction(factory) as session:
        save_stability_report(session, stability())
    with factory() as session:
        assert session.get(StabilityRow, "stability") is None
        assert get_run(session, "run").stage_states["perturb"].state == "skipped"


def test_decision_and_stage_update_are_atomic(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    with transaction(factory) as session:
        create_run(session, start())
        record_stage_state(session, "run", StageState(stage="decide", state="error"))
    with pytest.raises(InvalidTransition), transaction(factory) as session:
        save_decision(session, decision())
    with factory() as session:
        assert session.get(DecisionRow, "decision") is None
        assert get_run(session, "run").stage_states["decide"].state == "error"


@pytest.mark.parametrize("result", ["stability", "decision"])
def test_outcomes_rejected_after_run_finishes(
    factory: sessionmaker[Session],
    registry: None,
    result: str,
) -> None:
    with transaction(factory) as session:
        prepare(session)
        finish_run(session, "run", RunFinish(status="timeout", finished_at=NOW))
    with pytest.raises(InvalidTransition), transaction(factory) as session:
        if result == "stability":
            save_stability_report(session, stability())
        else:
            save_decision(session, decision())
