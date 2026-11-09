"""Configurable SQLite engines and short, caller-owned transaction boundaries."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from warrant.db.errors import PersistenceError, storage_errors


class DbSettings(BaseModel):
    """Local database URL and bounded writer-lock wait."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    url: str = "sqlite:///data/warrant.db"
    busy_timeout_ms: StrictInt = Field(default=5000, ge=0, le=60000)

    @field_validator("url")
    @classmethod
    def sqlite_url(cls, value: str) -> str:
        """Accept standard local SQLite URLs for this prototype."""
        url = make_url(value)
        if url.drivername not in {"sqlite", "sqlite+pysqlite"} or url.query:
            raise ValueError("Use a standard sqlite:///path.db or sqlite:///:memory: URL")
        return value


def create_db_engine(settings: DbSettings) -> Engine:
    """Create an engine with per-connection integrity and file-backed WAL."""
    database = make_url(settings.url).database
    memory = database in {None, "", ":memory:"}
    if not memory:
        assert database is not None
        Path(database).resolve().parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(database, autocommit=True) as bootstrap:
            mode = bootstrap.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            if mode != "wal":
                raise PersistenceError("Could not initialize WAL mode")
    engine = create_engine(
        settings.url,
        connect_args={"autocommit": False, "check_same_thread": False},
        **({"poolclass": StaticPool} if memory else {}),
    )

    @event.listens_for(engine, "connect")
    def configure(connection: sqlite3.Connection, _record: object) -> None:
        previous = connection.autocommit
        connection.autocommit = True
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(f"PRAGMA busy_timeout={settings.busy_timeout_ms:d}")
        finally:
            connection.autocommit = previous

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a factory; each request/thread owns a separate session."""
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def transaction(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Commit on success, rollback on failure, and always close the session."""
    with factory() as session, storage_errors(), session.begin():
        yield session
