"""A teammate can migrate and seed a local database from a clean process."""

import json
import os
import subprocess
import sys
from pathlib import Path


def command(database: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["TRUSSTED_DB_URL"] = f"sqlite:///{database}"
    return subprocess.run(
        [sys.executable, "-m", "trussted.cli.main", "db", *arguments],
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def test_teammate_can_migrate_and_seed_twice(tmp_path: Path) -> None:
    database = tmp_path / "demo.db"
    result = command(database, "migrate")
    assert result.returncode == 0, result.stderr
    seed_args = (
        "seed",
        "--scenario-dir",
        "examples/db/scenarios",
        "--fixture-root",
        "examples/db/fixtures",
    )
    first = command(database, *seed_args)
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)["scenarios_created"] == 1
    second = command(database, *seed_args)
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout)["scenarios_created"] == 0
    assert database.is_file()


def test_bad_seed_exits_nonzero(tmp_path: Path) -> None:
    database = tmp_path / "invalid.db"
    assert command(database, "migrate").returncode == 0
    result = command(database, "seed", "--scenario-dir", str(tmp_path / "absent"))
    assert result.returncode != 0
    assert "Traceback" not in result.stderr


def test_unusable_database_path_exits_without_traceback(tmp_path: Path) -> None:
    result = command(tmp_path, "migrate")
    assert result.returncode == 1
    assert "Database command failed" in result.stderr
    assert "Traceback" not in result.stderr
