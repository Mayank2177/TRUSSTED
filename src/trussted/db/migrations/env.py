"""Alembic environment for CLI URLs or a caller-supplied connection."""

import os

from alembic import context
from sqlalchemy import Connection

import trussted.db.tables  # noqa: F401
from trussted.db.base import Base
from trussted.db.session import DbSettings, create_db_engine

config = context.config
target_metadata = Base.metadata


def run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=os.environ.get("TRUSSTED_DB_URL", "sqlite:///data/trussted.db"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
elif connection := config.attributes.get("connection"):
    run_migrations(connection)
else:
    engine = create_db_engine(
        DbSettings(url=os.environ.get("TRUSSTED_DB_URL", "sqlite:///data/trussted.db"))
    )
    try:
        with engine.connect() as connection:
            run_migrations(connection)
    finally:
        engine.dispose()
