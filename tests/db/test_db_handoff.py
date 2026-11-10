"""Cross-module storage handoff, independent of live LLM or payment services."""

from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session, sessionmaker

from tests.db.audit_helpers import accept_external_signature, receipt_bundle
from tests.db.conftest import NOW
from tests.db.test_runs import start
from trussted.db.contracts.evidence import (
    FactConflictInput,
    ObservationInput,
    ProductFactInput,
    RankingInput,
    SourceSpan,
)
from trussted.db.contracts.outcomes import DecisionInput, StabilityInput
from trussted.db.contracts.receipts import SigningKeyInput
from trussted.db.contracts.registry import ScenarioInput
from trussted.db.contracts.runs import RunFinish, StageState
from trussted.db.migrate import migrate
from trussted.db.repositories.evidence import (
    save_fact_conflicts,
    save_observations,
    save_product_facts,
    save_ranking,
)
from trussted.db.repositories.outcomes import save_decision, save_stability_report
from trussted.db.repositories.queries import get_benchmark_counts, get_run_detail
from trussted.db.repositories.receipts import (
    get_receipt,
    register_signing_key,
    save_finalized_receipt,
)
from trussted.db.repositories.registry import register_scenario
from trussted.db.repositories.runs import create_run, finish_run, record_stage_state
from trussted.db.session import DbSettings, create_db_engine, create_session_factory, transaction


def test_complete_storage_handoff(factory: sessionmaker[Session], registry: None) -> None:
    with transaction(factory) as session:
        create_run(session, start())
    with transaction(factory) as session:
        save_observations(
            session,
            [
                ObservationInput(
                    id="observation",
                    run_id="run",
                    url="http://127.0.0.1/page",
                    content_hash="a" * 64,
                    byte_size=100,
                    fetched_at=NOW,
                )
            ],
        )
        save_product_facts(
            session,
            [
                ProductFactInput(
                    id="fact",
                    run_id="run",
                    observation_id="observation",
                    sku="storage-32",
                    name="Synthetic storage",
                    price_minor=49900,
                    currency="INR",
                    spec={"capacity_gb": 128},
                    seller_id="synthetic-shop",
                    source_span=SourceSpan(start=0, end=20),
                )
            ],
        )
        save_fact_conflicts(
            session,
            [
                FactConflictInput(
                    id="conflict",
                    fact_id="fact",
                    field="capacity_gb",
                    extracted_value=128,
                    reference_value=32,
                    severity="high",
                    reference_source="synthetic catalog",
                )
            ],
        )
        save_ranking(
            session,
            RankingInput(
                id="ranking",
                run_id="run",
                perturbation="none",
                ordered_fact_ids=("fact",),
                scores={"fact": 1.0},
                winner_fact_id="fact",
            ),
        )
        save_stability_report(
            session,
            StabilityInput(
                id="stability",
                run_id="run",
                winner_counts={"fact": 6},
                stable=True,
                threshold=1.0,
                flips=[],
            ),
        )
        save_decision(
            session,
            DecisionInput(
                id="decision",
                run_id="run",
                result="BLOCK",
                reasons=("FACT_CONFLICT_HIGH",),
                policy_version="1",
                amount_minor=49900,
                currency="INR",
            ),
        )
    with transaction(factory) as session:
        register_signing_key(
            session,
            SigningKeyInput(
                id="key",
                algorithm="ed25519",
                public_key="synthetic-public-key",
                created_at=NOW,
            ),
        )
        # Only the external crypto boundary is replaced; DB/chain checks remain real.
        save_finalized_receipt(session, receipt_bundle(), verify=accept_external_signature)
        record_stage_state(session, "run", StageState(stage="receipt", state="completed"))
        finish_run(
            session,
            "run",
            RunFinish(
                status="completed",
                finished_at=NOW + timedelta(seconds=3),
                attacker_success=False,
                latency_ms=3000,
                llm_cost_micro_usd=100,
            ),
        )
        register_scenario(
            session,
            ScenarioInput(
                id="attack-v2",
                scenario_key="attack",
                title="Revised",
                kind="attack",
                definition={"changed": True},
                expected_outcome="revised case",
                version=2,
            ),
        )
        create_run(session, start("error", repetition=2))
        finish_run(session, "error", RunFinish(status="timeout", finished_at=NOW))
    with factory() as session:
        detail = get_run_detail(session, "run")
        receipt = get_receipt(session, "receipt")
        counts = get_benchmark_counts(session, "batch")[0]
    assert detail.scenario.version == 1
    assert detail.product_facts[0].source_span.end == 20
    assert detail.fact_conflicts[0].reference_value == 32
    assert detail.rankings[0].ordered_fact_ids == ("fact",)
    assert detail.stability_report is not None and detail.stability_report.stable
    assert detail.decision is not None and detail.decision.reasons == ("FACT_CONFLICT_HIGH",)
    assert receipt.bundle.events[1].prev_hash == receipt.bundle.events[0].event_hash
    assert (counts.attack_eligible, counts.attack_successes, counts.timeout) == (1, 0, 1)


@pytest.mark.parametrize(
    "revision",
    [
        "0001_registry",
        "0002_runs",
        "0003_evidence",
        "0004_outcomes",
        "0005_receipts",
        "0006_credentials",
    ],
)
def test_each_schema_revision_upgrades_without_losing_data(tmp_path: Path, revision: str) -> None:
    engine = create_db_engine(DbSettings(url=f"sqlite:///{tmp_path / 'upgrade.db'}"))
    try:
        migrate(engine, revision)
        factory = create_session_factory(engine)
        with transaction(factory) as session:
            register_scenario(
                session,
                ScenarioInput(
                    id="historical",
                    scenario_key="historical",
                    title="Historical",
                    kind="benign",
                    definition={"original": True},
                    expected_outcome="preserved",
                    version=1,
                ),
            )
        migrate(engine)
        migrate(engine)
        with engine.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT definition FROM scenarios WHERE id='historical'"
                ).scalar_one()
                == '{"original":true}'
            )
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        assert len(set(inspect(engine).get_table_names()) - {"alembic_version"}) == 15
    finally:
        engine.dispose()
