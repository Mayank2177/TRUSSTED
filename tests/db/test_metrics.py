"""Benchmark counts must not turn errors or skipped checks into measured successes."""

from sqlalchemy.orm import Session, sessionmaker

from tests.db.conftest import NOW
from tests.db.test_runs import start
from warrant.db.contracts.runs import RunFinish, StageState
from warrant.db.repositories.queries import get_benchmark_counts, get_benchmark_samples
from warrant.db.repositories.runs import create_run, finish_run, record_stage_state
from warrant.db.session import transaction


def test_eligible_outcomes_and_failures_are_separate(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    with transaction(factory) as session:
        for index, outcome in enumerate([True, False, False], start=1):
            identifier = f"attack-{index}"
            create_run(session, start(identifier, repetition=index))
            finish_run(
                session,
                identifier,
                RunFinish(
                    status="completed",
                    finished_at=NOW,
                    attacker_success=outcome,
                ),
            )
        for index, status in enumerate(["error", "timeout"], start=4):
            identifier = f"attack-{index}"
            create_run(session, start(identifier, repetition=index))
            finish_run(session, identifier, RunFinish(status=status, finished_at=NOW))
        create_run(session, start("active", repetition=6))
        record_stage_state(session, "active", StageState(stage="perturb", state="skipped"))
        for index, blocked in enumerate([True, False], start=1):
            identifier = f"benign-{index}"
            create_run(session, start(identifier, scenario="benign", repetition=index))
            finish_run(
                session,
                identifier,
                RunFinish(
                    status="completed",
                    finished_at=NOW,
                    benign_success=not blocked,
                    false_block=blocked,
                ),
            )
    with factory() as session:
        rows = {row.scenario_id: row for row in get_benchmark_counts(session, "batch")}
        attack = rows["attack"]
        assert (attack.attack_eligible, attack.attack_successes) == (3, 1)
        assert (attack.error, attack.timeout, attack.attempted, attack.running) == (1, 1, 5, 1)
        benign = rows["benign"]
        assert (benign.false_block_eligible, benign.false_blocks) == (2, 1)
        assert benign.attack_eligible == 0
        samples = {row.run_id: row for row in get_benchmark_samples(session, "batch")}
        assert samples["active"].perturbation_state == "skipped"
        assert samples["active"].stable is None
        assert get_benchmark_counts(session, "absent") == ()
