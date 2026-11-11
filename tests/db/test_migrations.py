"""Alembic, rather than metadata.create_all, owns reproducible schema state."""

from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session, sessionmaker

from tests.db.conftest import NOW
from tests.db.test_runs import start
from warrant.db.contracts.registry import BatchInput, FixtureInput, ScenarioInput, VariantInput
from warrant.db.migrate import migrate
from warrant.db.repositories.registry import (
    create_batch,
    register_fixture,
    register_scenario,
    register_variant,
)
from warrant.db.repositories.runs import create_run
from warrant.db.session import (
    DbSettings,
    create_db_engine,
    create_session_factory,
    transaction,
)


def _create_run_registry(factory: sessionmaker[Session]) -> None:
    with transaction(factory) as session:
        register_scenario(
            session,
            ScenarioInput(
                id="attack",
                scenario_key="attack",
                title="attack",
                kind="attack",
                definition={},
                expected_outcome="synthetic",
                version=1,
            ),
        )
        register_fixture(
            session,
            FixtureInput(
                id="attack-page",
                scenario_id="attack",
                name="page",
                content_hash="a" * 64,
                path="attack.html",
                created_at=NOW,
            ),
        )
        register_variant(
            session,
            VariantInput(
                id="variant",
                name="warrant",
                model_name="synthetic",
                model_version="1",
                prompt_version="1",
                config={},
            ),
        )
        create_batch(session, BatchInput(id="batch", created_at=NOW, git_commit="test", seed=7))
        create_run(session, start())


def test_registry_migration_repeat_and_constraints(tmp_path: Path) -> None:
    engine = create_db_engine(DbSettings(url=f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}"))
    try:
        migrate(engine, "0001_registry")
        migrate(engine, "0001_registry")
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) == {
            "alembic_version",
            "scenarios",
            "fixtures",
            "agent_variants",
            "benchmark_batches",
        }
        assert {c["name"] for c in inspector.get_unique_constraints("scenarios")} == {
            "uq_scenarios_scenario_key_version"
        }
        assert {c["name"] for c in inspector.get_unique_constraints("fixtures")} == {
            "uq_fixtures_scenario_id_name"
        }
        assert {c["name"] for c in inspector.get_unique_constraints("agent_variants")} == {
            "uq_agent_variants_name_config_hash"
        }
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                == "0001_registry"
            )
            assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
    finally:
        engine.dispose()


def test_head_has_decision_winner_and_one_credential_per_run(
    factory: sessionmaker[Session], registry: None
) -> None:
    inspector = inspect(factory.kw["bind"])
    decisions = {column["name"] for column in inspector.get_columns("decisions")}
    assert {"winner_fact_id", "approval_hash"}.issubset(decisions)
    credentials = {column["name"] for column in inspector.get_columns("credentials")}
    assert "approval_hash" in credentials
    assert {"uq_credentials_run_id"}.issubset(
        {constraint["name"] for constraint in inspector.get_unique_constraints("credentials")}
    )
    foreign_keys = inspector.get_foreign_keys("decisions")
    assert any(
        fk["constrained_columns"] == ["winner_fact_id", "run_id"]
        and fk["referred_table"] == "product_facts"
        for fk in foreign_keys
    )


def test_duplicate_credential_migration_fails_without_changing_records(
    tmp_path: Path,
) -> None:
    engine = create_db_engine(
        DbSettings(url=f"sqlite:///{(tmp_path / 'before-0009.db').as_posix()}")
    )
    try:
        migrate(engine, "0008_decision_product_provenance")
        factory = create_session_factory(engine)
        _create_run_registry(factory)
        with engine.begin() as connection:
            for index in range(2):
                connection.execute(
                    text(
                        "INSERT INTO credentials "
                        "(id,run_id,cart_hash,merchant_id,amount_minor,currency,nonce,expires_at,"
                        "redeemed_at,signature,approval_hash) VALUES "
                        f"('credential-{index}','run',:hash,'merchant',1,'USD',:nonce,"
                        "'2030-01-01T00:00:00Z',NULL,'signature',NULL)"
                    ),
                    {"hash": "a" * 64, "nonce": f"nonce-{index}"},
                )
        with pytest.raises(RuntimeError, match="No records were changed"):
            migrate(engine)
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT COUNT(*) FROM credentials WHERE run_id='run'")) == 2
            )
    finally:
        engine.dispose()


def test_legacy_allow_migration_backfills_only_the_unique_base_ranking_winner(
    tmp_path: Path,
) -> None:
    from tests.db.test_evidence import fact, observation, ranking
    from warrant.db.repositories.evidence import save_observations, save_product_facts, save_ranking

    engine = create_db_engine(
        DbSettings(url=f"sqlite:///{(tmp_path / 'before-0008.db').as_posix()}")
    )
    try:
        migrate(engine, "0007_immutable_insert_guards")
        factory = create_session_factory(engine)
        _create_run_registry(factory)
        with transaction(factory) as session:
            save_observations(session, (observation(),))
            save_product_facts(session, (fact(),))
            save_ranking(session, ranking("none", "base-ranking"))
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO decisions "
                    "(id,run_id,result,reasons,policy_version,amount_minor,currency) "
                    "VALUES ('legacy-decision','run','ALLOW','[]','old-policy',1250,'USD')"
                )
            )
        migrate(engine, "head")
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT winner_fact_id, approval_hash FROM decisions WHERE id='legacy-decision'"
                )
            ).one()
            assert row.winner_fact_id == "fact"
            assert row.approval_hash is None
    finally:
        engine.dispose()
