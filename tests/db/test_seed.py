"""Synthetic YAML imports retain exact historical revisions and fixture bytes."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml
from sqlalchemy import Engine, func, select

from warrant.db.errors import DuplicateRecord, InvalidEvidence
from warrant.db.migrate import migrate
from warrant.db.seed import seed_database
from warrant.db.session import DbSettings, create_db_engine, create_session_factory, transaction
from warrant.db.tables.registry import FixtureRow, ScenarioRow

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CORPUS = Path(__file__).parents[1] / "fixtures" / "db"


@pytest.fixture
def seed_engine() -> Iterator[Engine]:
    engine = create_db_engine(DbSettings(url="sqlite:///:memory:"))
    migrate(engine, "0001_registry")
    yield engine
    engine.dispose()


def write_scenario(
    directory: Path,
    *,
    version: int = 1,
    title: str = "Synthetic scenario",
    path: str = "candidate.html",
    content_hash: str | None = None,
    filename: str = "scenario.yaml",
) -> None:
    directory.mkdir(exist_ok=True)
    fixture = {"name": "candidate", "path": path}
    if content_hash is not None:
        fixture["content_hash"] = content_hash
    (directory / filename).write_text(
        yaml.safe_dump(
            {
                "scenario_key": "synthetic",
                "version": version,
                "title": title,
                "kind": "attack",
                "attack_type": "prompt_injection",
                "definition": {"sku": "synthetic-A"},
                "expected_outcome": "synthetic wrong SKU",
                "fixtures": [fixture],
            }
        ),
        encoding="utf-8",
    )


def test_seed_is_idempotent(seed_engine: Engine) -> None:
    factory = create_session_factory(seed_engine)
    with transaction(factory) as session:
        first = seed_database(
            session, scenario_dir=CORPUS / "scenarios", fixture_root=CORPUS / "storefronts", now=NOW
        )
    with transaction(factory) as session:
        second = seed_database(
            session,
            scenario_dir=CORPUS / "scenarios",
            fixture_root=CORPUS / "storefronts",
            now=NOW + timedelta(days=1),
        )
    assert (first.scenarios_created, first.fixtures_created, first.unchanged) == (1, 1, 0)
    assert (second.scenarios_created, second.fixtures_created, second.unchanged) == (0, 0, 2)
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(ScenarioRow)) == 1
        fixture = session.scalars(select(FixtureRow)).one()
        assert fixture.path == "candidate.html"
        assert fixture.created_at == "2026-01-01T00:00:00.000000Z"


def test_new_revision_keeps_old_revision(seed_engine: Engine, tmp_path: Path) -> None:
    factory = create_session_factory(seed_engine)
    directory = tmp_path / "scenarios"
    write_scenario(directory)
    with transaction(factory) as session:
        seed_database(session, scenario_dir=directory, fixture_root=CORPUS / "storefronts", now=NOW)
        original = dict(session.get(ScenarioRow, "synthetic@1").__dict__)
        original.pop("_sa_instance_state")
    write_scenario(directory, version=2, title="Changed revision")
    with transaction(factory) as session:
        summary = seed_database(
            session, scenario_dir=directory, fixture_root=CORPUS / "storefronts", now=NOW
        )
        assert (summary.scenarios_created, summary.fixtures_created) == (1, 1)
        old = session.get(ScenarioRow, "synthetic@1")
        assert old is not None
        assert {key: getattr(old, key) for key in original} == original
        assert session.get(ScenarioRow, "synthetic@2") is not None


def test_same_revision_changed_content_is_rejected(seed_engine: Engine, tmp_path: Path) -> None:
    factory = create_session_factory(seed_engine)
    directory = tmp_path / "scenarios"
    write_scenario(directory)
    with transaction(factory) as session:
        seed_database(session, scenario_dir=directory, fixture_root=CORPUS / "storefronts", now=NOW)
    write_scenario(directory, title="Rewritten")
    with pytest.raises(DuplicateRecord), transaction(factory) as session:
        seed_database(session, scenario_dir=directory, fixture_root=CORPUS / "storefronts", now=NOW)


@pytest.mark.parametrize(
    "path,hash_value",
    [
        ("candidate.html", "0" * 64),
        ("../outside.html", None),
        ("missing.html", None),
    ],
)
def test_invalid_fixture_leaves_no_partial_registry(
    seed_engine: Engine,
    tmp_path: Path,
    path: str,
    hash_value: str | None,
) -> None:
    directory = tmp_path / "scenarios"
    root = tmp_path / "storefronts"
    root.mkdir()
    (root / "candidate.html").write_bytes(b"synthetic")
    (tmp_path / "outside.html").write_bytes(b"existing outside file")
    write_scenario(directory, filename="a-valid.yaml")
    write_scenario(directory, version=2, path=path, content_hash=hash_value, filename="b-bad.yaml")
    factory = create_session_factory(seed_engine)
    with transaction(factory) as session:
        with pytest.raises(InvalidEvidence):
            seed_database(session, scenario_dir=directory, fixture_root=root, now=NOW)
        assert session.scalar(select(func.count()).select_from(ScenarioRow)) == 0
        assert session.scalar(select(func.count()).select_from(FixtureRow)) == 0


def test_fixture_change_under_same_revision_rejected(seed_engine: Engine, tmp_path: Path) -> None:
    directory = tmp_path / "scenarios"
    root = tmp_path / "fixtures"
    root.mkdir()
    page = root / "candidate.html"
    page.write_text("first", encoding="utf-8")
    write_scenario(directory)
    factory = create_session_factory(seed_engine)
    with transaction(factory) as session:
        seed_database(session, scenario_dir=directory, fixture_root=root, now=NOW)
    page.write_text("rewritten", encoding="utf-8")
    with pytest.raises(DuplicateRecord), transaction(factory) as session:
        seed_database(session, scenario_dir=directory, fixture_root=root, now=NOW)


def test_same_revision_failure_rolls_back_new_rows_even_when_caught(
    seed_engine: Engine,
    tmp_path: Path,
) -> None:
    directory = tmp_path / "scenarios"
    write_scenario(directory, filename="z-old.yaml")
    factory = create_session_factory(seed_engine)
    with transaction(factory) as session:
        seed_database(session, scenario_dir=directory, fixture_root=CORPUS / "storefronts", now=NOW)
    write_scenario(directory, version=2, filename="a-new.yaml")
    write_scenario(directory, title="Rewritten", filename="z-old.yaml")
    with transaction(factory) as session:
        with pytest.raises(DuplicateRecord):
            seed_database(
                session, scenario_dir=directory, fixture_root=CORPUS / "storefronts", now=NOW
            )
        assert session.scalar(select(func.count()).select_from(ScenarioRow)) == 1
        assert session.get(ScenarioRow, "synthetic@2") is None
