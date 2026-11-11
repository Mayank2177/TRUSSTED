"""Regressions reproduced during the independent whole-branch review."""

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from tests.db.audit_helpers import accept_external_signature, prepare_receipt, receipt_bundle
from warrant.db.errors import PersistenceError
from warrant.db.repositories.receipts import save_finalized_receipt
from warrant.db.session import DbSettings, create_db_engine, transaction


@pytest.mark.parametrize(
    "statement",
    [
        """INSERT OR REPLACE INTO scenarios
       (id, scenario_key, title, kind, attack_type, definition, expected_outcome, version)
       SELECT id, scenario_key, 'rewritten', kind, attack_type,
              definition, expected_outcome, version
       FROM scenarios WHERE id='attack'""",
        """INSERT OR REPLACE INTO receipt_events
       (id, receipt_id, seq, type, payload, payload_hash, prev_hash, event_hash, created_at)
       SELECT id, receipt_id, seq, 'facts', payload, payload_hash, prev_hash, event_hash, created_at
       FROM receipt_events WHERE id='event-0'""",
        """INSERT OR REPLACE INTO scenarios
       (id, scenario_key, title, kind, attack_type, definition, expected_outcome, version)
       SELECT 'new-scenario', scenario_key, 'rewritten', kind, attack_type,
              definition, expected_outcome, version
       FROM scenarios WHERE id='attack'""",
        """INSERT OR REPLACE INTO receipt_events
       (id, receipt_id, seq, type, payload, payload_hash, prev_hash, event_hash, created_at)
       SELECT 'new-event', receipt_id, seq, 'facts', payload,
              payload_hash, prev_hash, event_hash, created_at
       FROM receipt_events WHERE id='event-0'""",
        """INSERT OR REPLACE INTO receipts
       (id, run_id, final_hash, signature, signing_key_id, created_at, export_path)
       SELECT id, run_id, final_hash, 'rewritten', signing_key_id, created_at, export_path
       FROM receipts WHERE id='receipt'""",
        """INSERT OR REPLACE INTO receipts
       (id, run_id, final_hash, signature, signing_key_id, created_at, export_path)
       SELECT 'new-receipt', run_id, final_hash, 'rewritten',
              signing_key_id, created_at, export_path
       FROM receipts WHERE id='receipt'""",
    ],
)
@pytest.mark.parametrize("recursive", [True, False])
def test_replace_cannot_rewrite_immutable_evidence(
    factory: sessionmaker[Session],
    registry: None,
    statement: str,
    recursive: bool,
) -> None:
    with transaction(factory) as session:
        prepare_receipt(session)
        save_finalized_receipt(session, receipt_bundle(), verify=accept_external_signature)
    with pytest.raises(PersistenceError):
        with transaction(factory) as session:
            session.execute(text(f"PRAGMA recursive_triggers={int(recursive)}"))
            session.execute(text(statement))
    with factory() as session:
        assert (
            session.execute(text("SELECT title FROM scenarios WHERE id='attack'")).scalar_one()
            == "attack"
        )
        assert (
            session.execute(text("SELECT type FROM receipt_events WHERE id='event-0'")).scalar_one()
            == "intent"
        )


def test_unusable_database_path_is_a_typed_setup_error(tmp_path: Path) -> None:
    with pytest.raises(PersistenceError):
        create_db_engine(DbSettings(url=f"sqlite:///{tmp_path}"))
