"""Minimal CLI shell; teammates can register pipeline commands alongside db."""

import argparse
import os
from collections.abc import Sequence

from trussted.cli.db import register_db_commands, run_db_command


def main(argv: Sequence[str] | None = None) -> int:
    """Run a command and return a shell exit status."""
    parser = argparse.ArgumentParser(prog="trussted")
    parser.add_argument(
        "--db-url", default=os.getenv("TRUSSTED_DB_URL", "sqlite:///data/trussted.db")
    )
    register_db_commands(parser.add_subparsers(dest="resource", required=True))
    arguments = parser.parse_args(argv)
    return run_db_command(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
