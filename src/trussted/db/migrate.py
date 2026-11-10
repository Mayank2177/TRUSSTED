"""Programmatic Alembic entry point using the caller's configured engine."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine


def migrate(engine: Engine, revision: str = "head") -> None:
    """Upgrade schema using packaged migrations and an existing connection."""
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, revision)
