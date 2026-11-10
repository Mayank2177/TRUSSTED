"""Load a small, explicit scenario corpus without rewriting historical inputs.

Each ``*.yaml``/``*.yml`` file holds one mapping with required ``scenario_key``,
``version``, ``title``, ``kind`` (attack/benign), ``definition`` (JSON),
``expected_outcome`` (text), and ``fixtures`` (a nonempty list). ``attack_type``
is optional. Each fixture requires ``name`` and a path relative to fixture_root;
optional ``content_hash`` verifies the SHA-256 calculated from the file bytes.
Unknown fields are rejected. Scenario IDs are ``scenario_key@version``. Fixture
IDs are ``fixture-`` plus a SHA-256 of the scenario/name/content identity envelope.
Fixture bytes remain on disk. A changed fixture set requires a new revision.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import Field, JsonValue, StrictInt, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from trussted.db.contracts import FrozenModel, Hash, Id
from trussted.db.contracts.registry import FixtureInput, ScenarioInput
from trussted.db.errors import DuplicateRecord, InvalidEvidence
from trussted.db.repositories.registry import register_fixture, register_scenario
from trussted.db.tables.registry import FixtureRow, ScenarioRow
from trussted.db.values import canonical_json, sha256_hex, utc_datetime


class SeedSummary(FrozenModel):
    scenarios_created: Annotated[StrictInt, Field(ge=0)]
    fixtures_created: Annotated[StrictInt, Field(ge=0)]
    unchanged: Annotated[StrictInt, Field(ge=0)]


class _FixtureSpec(FrozenModel):
    name: Id
    path: Annotated[str, Field(min_length=1)]
    content_hash: Hash | None = None


class _ScenarioSpec(FrozenModel):
    scenario_key: Id
    version: Annotated[StrictInt, Field(ge=1)]
    title: Annotated[str, Field(min_length=1)]
    kind: Literal["attack", "benign"]
    attack_type: str | None = None
    definition: JsonValue
    expected_outcome: Annotated[str, Field(min_length=1)]
    fixtures: Annotated[tuple[_FixtureSpec, ...], Field(min_length=1)]


@dataclass(frozen=True)
class _PreparedScenario:
    scenario: ScenarioInput
    fixtures: tuple[FixtureInput, ...]


def _prepare(scenario_dir: Path, fixture_root: Path, now: datetime) -> list[_PreparedScenario]:
    """Validate the complete input batch and file bytes before the first write."""
    try:
        root = fixture_root.resolve(strict=True)
        directory = scenario_dir.resolve(strict=True)
        if not root.is_dir() or not directory.is_dir():
            raise ValueError("Scenario directory and fixture root must be directories")
        prepared = []
        identities = set()
        sources = sorted([*directory.glob("*.yaml"), *directory.glob("*.yml")])
        for source in sources:
            spec = _ScenarioSpec.model_validate(yaml.safe_load(source.read_text(encoding="utf-8")))
            identity = f"{spec.scenario_key}@{spec.version}"
            if identity in identities:
                raise ValueError("Corpus contains a duplicate scenario revision")
            identities.add(identity)
            scenario = ScenarioInput.model_validate(
                {
                    **spec.model_dump(exclude={"fixtures"}),
                    "id": identity,
                }
            )
            fixtures = []
            names = set()
            for fixture in spec.fixtures:
                if fixture.name in names:
                    raise ValueError("Scenario contains a duplicate fixture name")
                names.add(fixture.name)
                relative = Path(fixture.path)
                if relative.is_absolute():
                    raise ValueError("Fixture path must be relative to fixture_root")
                resolved = (root / relative).resolve(strict=True)
                if not resolved.is_relative_to(root) or not resolved.is_file():
                    raise ValueError("Fixture path must identify a file inside fixture_root")
                content_hash = sha256_hex(resolved.read_bytes())
                if fixture.content_hash is not None and fixture.content_hash != content_hash:
                    raise ValueError("Fixture content hash does not match its file bytes")
                envelope: dict[str, JsonValue] = {
                    "scenario_id": identity,
                    "name": fixture.name,
                    "content_hash": content_hash,
                }
                fixture_id = "fixture-" + sha256_hex(canonical_json(envelope).encode("utf-8"))
                fixtures.append(
                    FixtureInput(
                        id=fixture_id,
                        scenario_id=identity,
                        name=fixture.name,
                        content_hash=content_hash,
                        path=resolved.relative_to(root).as_posix(),
                        created_at=now,
                    )
                )
            prepared.append(_PreparedScenario(scenario, tuple(fixtures)))
        return prepared
    except (OSError, ValueError, ValidationError, yaml.YAMLError) as error:
        raise InvalidEvidence("Scenario corpus or fixture file is invalid") from error


def seed_database(
    session: Session,
    *,
    scenario_dir: Path,
    fixture_root: Path,
    now: datetime,
) -> SeedSummary:
    """Atomically register a validated corpus; leave commit to the caller.

    ``unchanged`` counts both scenario and fixture rows. Exact repeats preserve
    original fixture timestamps even if the injected clock has advanced.
    """
    prepared = _prepare(scenario_dir, fixture_root, utc_datetime(now))
    scenarios_created = fixtures_created = unchanged = 0
    with session.begin_nested():
        for item in prepared:
            existing = session.get(ScenarioRow, item.scenario.id)
            if existing is not None:
                # register_scenario also verifies every persisted definition field.
                register_scenario(session, item.scenario)
                stored = session.scalars(
                    select(FixtureRow).where(
                        FixtureRow.scenario_id == item.scenario.id,
                    )
                ).all()
                stored_identity = {(row.id, row.name, row.content_hash, row.path) for row in stored}
                expected_identity = {
                    (row.id, row.name, row.content_hash, row.path) for row in item.fixtures
                }
                if stored_identity != expected_identity:
                    raise DuplicateRecord(
                        "Changed fixture definitions require a new scenario revision"
                    )
                unchanged += 1 + len(stored)
            else:
                register_scenario(session, item.scenario)
                scenarios_created += 1
                for fixture in item.fixtures:
                    register_fixture(session, fixture)
                    fixtures_created += 1
    return SeedSummary(
        scenarios_created=scenarios_created, fixtures_created=fixtures_created, unchanged=unchanged
    )
