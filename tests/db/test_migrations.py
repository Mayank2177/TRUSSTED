"""Alembic, rather than metadata.create_all, owns reproducible schema state."""

from pathlib import Path

from sqlalchemy import inspect, text

from warrant.db.migrate import migrate
from warrant.db.session import DbSettings, create_db_engine


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
