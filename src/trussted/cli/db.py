"""Database migration/seeding adapters; business logic stays in db repositories."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from alembic.util.exc import CommandError
from sqlalchemy.exc import SQLAlchemyError

from trussted.db.errors import PersistenceError
from trussted.db.migrate import migrate
from trussted.db.seed import seed_database
from trussted.db.session import DbSettings, create_db_engine, create_session_factory, transaction


def register_db_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the db command group with a team-owned CLI parser."""
    parser = subparsers.add_parser("db", help="Local database setup")
    operations = parser.add_subparsers(dest="db_command", required=True)
    operations.add_parser("migrate", help="Apply all Alembic migrations")
    seed = operations.add_parser("seed", help="Register immutable scenarios and fixture hashes")
    seed.add_argument("--scenario-dir", type=Path, default=Path("bench/scenarios"))
    seed.add_argument("--fixture-root", type=Path, default=Path("bench/storefronts"))


def run_db_command(arguments: argparse.Namespace) -> int:
    """Execute the database boundary and print a small machine-readable result."""
    engine = None
    try:
        engine = create_db_engine(DbSettings(url=arguments.db_url))
        if arguments.db_command == "migrate":
            migrate(engine)
            print(json.dumps({"migration": "head"}))
        else:
            with transaction(create_session_factory(engine)) as session:
                summary = seed_database(
                    session,
                    scenario_dir=arguments.scenario_dir,
                    fixture_root=arguments.fixture_root,
                    now=datetime.now(UTC),
                )
            print(summary.model_dump_json())
        return 0
    except (PersistenceError, SQLAlchemyError, CommandError, OSError, ValueError) as error:
        # Do not print arbitrary validation input, HTML, tokens or exception payloads.
        print(
            f"Database command failed ({type(error).__name__}). Check setup and inputs.",
            file=sys.stderr,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()
