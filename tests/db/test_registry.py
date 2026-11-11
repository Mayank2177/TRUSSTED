"""Registry revisions and version envelopes cannot silently replace history."""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import IntegrityError

from warrant.db.contracts.registry import BatchInput, FixtureInput, ScenarioInput, VariantInput
from warrant.db.errors import DuplicateRecord, InvalidEvidence
from warrant.db.migrate import migrate
from warrant.db.repositories.registry import (
    create_batch,
    register_fixture,
    register_scenario,
    register_variant,
)
from warrant.db.session import DbSettings, create_db_engine, create_session_factory, transaction
from warrant.db.tables.registry import BatchRow, FixtureRow, ScenarioRow, VariantRow


@pytest.fixture
def registry_engine() -> Iterator[Engine]:
    engine = create_db_engine(DbSettings(url="sqlite:///:memory:"))
    migrate(engine, "0001_registry")
    yield engine
    engine.dispose()


def scenario(**changes: object) -> ScenarioInput:
    data: dict[str, object] = dict(
        id="S5@1",
        scenario_key="S5",
        title="Spec swap",
        kind="attack",
        attack_type="prompt_injection",
        definition={"sku": "A"},
        expected_outcome="wrong SKU purchased",
        version=1,
    )
    data.update(changes)
    return ScenarioInput.model_validate(data)


def variant(**changes: object) -> VariantInput:
    data: dict[str, object] = dict(
        id="variant-1",
        name="warrant",
        model_name="model",
        model_version="v1",
        prompt_version="p1",
        config={"seed": 1},
    )
    data.update(changes)
    return VariantInput.model_validate(data)


def test_scenario_revisions_pin_distinct_ids(registry_engine: Engine) -> None:
    factory = create_session_factory(registry_engine)
    with transaction(factory) as session:
        assert register_scenario(session, scenario()) == "S5@1"
        assert register_scenario(session, scenario(id="S5@2", version=2)) == "S5@2"
    with factory() as session:
        rows = session.scalars(select(ScenarioRow).order_by(ScenarioRow.version)).all()
        assert [(row.id, row.scenario_key, row.version) for row in rows] == [
            ("S5@1", "S5", 1),
            ("S5@2", "S5", 2),
        ]


def test_exact_registration_replays_but_conflicting_identity_rejected(
    registry_engine: Engine,
) -> None:
    factory = create_session_factory(registry_engine)
    with transaction(factory) as session:
        register_scenario(session, scenario())
        assert register_scenario(session, scenario()) == "S5@1"
    for changed in [scenario(id="other"), scenario(title="changed")]:
        with pytest.raises(DuplicateRecord), transaction(factory) as session:
            register_scenario(session, changed)


def test_variant_hash_covers_model_prompt_and_config(registry_engine: Engine) -> None:
    factory = create_session_factory(registry_engine)
    with transaction(factory) as session:
        register_variant(session, variant())
        register_variant(session, variant(id="variant-2", model_version="v2"))
        register_variant(session, variant(id="variant-3", prompt_version="p2"))
        register_variant(session, variant(id="variant-4", config={"seed": 2}))
        assert register_variant(session, variant()) == "variant-1"
        assert len({row.config_hash for row in session.scalars(select(VariantRow))}) == 4
    with pytest.raises(InvalidEvidence), transaction(factory) as session:
        register_variant(session, variant(id="bad", config_hash="0" * 64))
    with pytest.raises(DuplicateRecord), transaction(factory) as session:
        register_variant(session, variant(id="another"))


def test_fixture_foreign_key_and_uniqueness(registry_engine: Engine) -> None:
    factory = create_session_factory(registry_engine)
    fixture = FixtureInput(
        id="f1",
        scenario_id="S5@1",
        name="candidate",
        content_hash="a" * 64,
        path="candidate.html",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    with pytest.raises(InvalidEvidence) as captured, transaction(factory) as session:
        register_fixture(session, fixture)
    assert isinstance(captured.value.__cause__, IntegrityError)
    with transaction(factory) as session:
        register_scenario(session, scenario())
        register_fixture(session, fixture)
        assert register_fixture(session, fixture) == "f1"
    with pytest.raises(DuplicateRecord), transaction(factory) as session:
        register_fixture(session, fixture.model_copy(update={"id": "f2"}))
    with factory() as session:
        assert session.get(FixtureRow, "f1") is not None


def test_batch_flushes_without_committing(registry_engine: Engine) -> None:
    factory = create_session_factory(registry_engine)
    with pytest.raises(RuntimeError), transaction(factory) as session:
        assert (
            create_batch(
                session,
                BatchInput(
                    id="b1",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                    git_commit="abc123",
                    seed=5,
                    notes=None,
                ),
            )
            == "b1"
        )
        assert session.get(BatchRow, "b1") is not None
        raise RuntimeError("abort")
    with factory() as session:
        assert session.get(BatchRow, "b1") is None


def test_revision_database_protection(registry_engine: Engine) -> None:
    factory = create_session_factory(registry_engine)
    with transaction(factory) as session:
        register_scenario(session, scenario())
    for sql in [
        "UPDATE scenarios SET title='rewritten' WHERE id='S5@1'",
        "DELETE FROM scenarios WHERE id='S5@1'",
    ]:
        with pytest.raises(IntegrityError), registry_engine.begin() as connection:
            connection.execute(text(sql))


def test_input_models_frozen_and_reject_unknown_or_naive() -> None:
    with pytest.raises(ValidationError):
        scenario().title = "changed"
    with pytest.raises(ValidationError):
        scenario(unexpected=True)
    with pytest.raises(ValidationError):
        BatchInput(id="b1", created_at=datetime(2026, 1, 1), git_commit="abc", seed=1)
