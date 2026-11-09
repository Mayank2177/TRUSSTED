"""Isolated migration-backed databases and shared synthetic test records."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Literal

import pytest
from sqlalchemy.orm import Session, sessionmaker

from warrant.db.session import (
    DbSettings,
    create_db_engine,
    create_session_factory,
    transaction,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def factory() -> Iterator[sessionmaker[Session]]:
    from warrant.db.migrate import migrate

    engine = create_db_engine(DbSettings(url="sqlite:///:memory:"))
    migrate(engine)
    yield create_session_factory(engine)
    engine.dispose()


@pytest.fixture
def registry(factory: sessionmaker[Session]) -> None:
    from warrant.db.contracts.registry import BatchInput, FixtureInput, ScenarioInput, VariantInput
    from warrant.db.repositories.registry import (
        create_batch,
        register_fixture,
        register_scenario,
        register_variant,
    )

    scenarios: tuple[tuple[str, Literal["attack", "benign"]], ...] = (
        ("attack", "attack"),
        ("benign", "benign"),
    )
    with transaction(factory) as session:
        for key, kind in scenarios:
            register_scenario(
                session,
                ScenarioInput(
                    id=key,
                    scenario_key=key,
                    title=key,
                    kind=kind,
                    definition={},
                    expected_outcome="synthetic expected outcome",
                    version=1,
                ),
            )
            register_fixture(
                session,
                FixtureInput(
                    id=f"{key}-page",
                    scenario_id=key,
                    name="page",
                    content_hash="a" * 64,
                    path=f"{key}.html",
                    created_at=NOW,
                ),
            )
        register_variant(
            session,
            VariantInput(
                id="variant",
                name="warrant",
                model_name="stub",
                model_version="1",
                prompt_version="1",
                config={},
            ),
        )
        create_batch(session, BatchInput(id="batch", created_at=NOW, git_commit="abc", seed=1))
