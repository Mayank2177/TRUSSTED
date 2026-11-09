"""Migration-installed guards protect receipts against direct SQL mutations."""

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from tests.db.audit_helpers import (
    accept_external_signature,
    prepare_minimal_registry,
    prepare_receipt,
    receipt_bundle,
)
from warrant.db.errors import InvalidEvidence
from warrant.db.migrate import migrate
from warrant.db.repositories.receipts import save_finalized_receipt
from warrant.db.session import DbSettings, create_db_engine, create_session_factory, transaction


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE receipts SET export_path = 'changed'",
        "DELETE FROM receipts",
        "UPDATE receipt_events SET type = 'facts'",
        "DELETE FROM receipt_events",
        "DELETE FROM runs WHERE id = 'run'",
        "DELETE FROM signing_keys WHERE id = 'key'",
    ],
)
def test_receipt_mutations_and_parent_deletion_fail(
    factory: sessionmaker[Session],
    registry: None,
    statement: str,
) -> None:
    with transaction(factory) as session:
        prepare_receipt(session)
        save_finalized_receipt(session, receipt_bundle(), verify=accept_external_signature)
    with pytest.raises(InvalidEvidence):
        with transaction(factory) as session:
            session.execute(text(statement))
    with factory() as session:
        assert session.scalar(text("SELECT count(*) FROM receipts")) == 1
        assert session.scalar(text("SELECT count(*) FROM receipt_events")) == 2


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE receipts SET export_path = 'changed'",
        "DELETE FROM receipts",
        "UPDATE receipt_events SET type = 'facts'",
        "DELETE FROM receipt_events",
    ],
)
def test_file_migration_installs_and_enforces_receipt_mutation_triggers(
    tmp_path: Path,
    statement: str,
) -> None:
    engine = create_db_engine(DbSettings(url=f"sqlite:///{(tmp_path / 'receipts.db').as_posix()}"))
    try:
        migrate(engine)
        with engine.connect() as connection:
            triggers = set(
                connection.scalars(
                    text(
                        "SELECT name FROM sqlite_master WHERE type = 'trigger' "
                        "AND tbl_name IN ('receipts', 'receipt_events')"
                    )
                )
            )
            assert triggers == {
                "receipts_no_update",
                "receipts_no_delete",
                "receipt_events_no_update",
                "receipt_events_no_delete",
            }
            assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
        factory = create_session_factory(engine)
        with transaction(factory) as session:
            prepare_minimal_registry(session)
            prepare_receipt(session)
            save_finalized_receipt(session, receipt_bundle(), verify=accept_external_signature)
        with pytest.raises(InvalidEvidence):
            with transaction(factory) as session:
                session.execute(text(statement))
        with factory() as session:
            assert session.scalar(text("SELECT count(*) FROM receipts")) == 1
            assert session.scalar(text("SELECT count(*) FROM receipt_events")) == 2
    finally:
        engine.dispose()
