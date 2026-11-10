"""Typed query results stay usable after sessions close and preserve pagination."""

import pytest
from sqlalchemy.orm import Session, sessionmaker

from tests.db.test_runs import start
from trussted.db.contracts.queries import RunFilter
from trussted.db.errors import RecordNotFound
from trussted.db.repositories.queries import get_run_detail, list_runs
from trussted.db.repositories.runs import create_run
from trussted.db.session import transaction


def test_run_details_are_detached(factory: sessionmaker[Session], registry: None) -> None:
    with transaction(factory) as session:
        create_run(session, start())
    with factory() as session:
        detail = get_run_detail(session, "run")
    assert detail.run.id == "run"
    assert detail.scenario.version == 1
    assert detail.variant.model_version == "1"
    assert detail.observations == ()
    assert detail.decision is None


def test_run_filters_and_stable_pagination(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    with transaction(factory) as session:
        create_run(session, start("b", repetition=2))
        create_run(session, start("a", repetition=1))
    with factory() as session:
        page = list_runs(session, RunFilter(batch_id="batch"), limit=1)
        assert [item.id for item in page.items] == ["a"]
        assert page.total == 2
        assert list_runs(session, RunFilter(), limit=1, offset=1).items[0].id == "b"
        assert list_runs(session, RunFilter(status="error")).total == 0
        with pytest.raises(ValueError):
            list_runs(session, RunFilter(), limit=101)
        with pytest.raises(RecordNotFound):
            get_run_detail(session, "absent")
