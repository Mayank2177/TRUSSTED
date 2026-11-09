"""Transactions must preserve data and enable SQLite integrity on every connection."""

from pathlib import Path

import pytest
from sqlalchemy import text

from warrant.db.session import (
    DbSettings,
    create_db_engine,
    create_session_factory,
    transaction,
)


def test_foreign_keys_on_every_connection(tmp_path: Path) -> None:
    engine = create_db_engine(DbSettings(url=f"sqlite:///{tmp_path / 'connections.db'}"))
    with engine.connect() as first, engine.connect() as second:
        assert first.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert second.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
    engine.dispose()


def test_file_database_uses_wal(tmp_path: Path) -> None:
    engine = create_db_engine(DbSettings(url=f"sqlite:///{tmp_path / 'wal.db'}"))
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "wal"
    engine.dispose()


def test_transaction_commits_and_rolls_back() -> None:
    engine = create_db_engine(DbSettings(url="sqlite:///:memory:"))
    factory = create_session_factory(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE checks (id INTEGER PRIMARY KEY)")
    with transaction(factory) as session:
        session.execute(text("INSERT INTO checks VALUES (1)"))
    with pytest.raises(RuntimeError, match="abort"):
        with transaction(factory) as session:
            session.execute(text("INSERT INTO checks VALUES (2)"))
            raise RuntimeError("abort")
    with factory() as session:
        assert session.execute(text("SELECT id FROM checks")).scalars().all() == [1]
    engine.dispose()


def test_in_memory_database_is_isolated() -> None:
    first = create_db_engine(DbSettings(url="sqlite:///:memory:"))
    second = create_db_engine(DbSettings(url="sqlite:///:memory:"))
    with first.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE private_table (id INTEGER)")
    with second.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM sqlite_master WHERE name='private_table'"
            ).scalar_one()
            == 0
        )
    first.dispose()
    second.dispose()


def test_invalid_settings() -> None:
    with pytest.raises(ValueError):
        DbSettings(url="sqlite:///:memory:", busy_timeout_ms=-1)


def test_disposed_engine_releases_database_file(tmp_path: Path) -> None:
    database = tmp_path / "released.db"
    engine = create_db_engine(DbSettings(url=f"sqlite:///{database}"))
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1
    engine.dispose()
    database.unlink()
    assert not database.exists()
