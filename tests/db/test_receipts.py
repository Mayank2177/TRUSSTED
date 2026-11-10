"""Persist complete chains; real cryptographic verification remains pending."""

from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from tests.db.audit_helpers import accept_external_signature, prepare_receipt, receipt_bundle
from tests.db.conftest import NOW
from trussted.db.errors import DuplicateRecord, InvalidEvidence, RecordNotFound
from trussted.db.repositories.receipts import (
    get_receipt,
    revoke_signing_key,
    save_finalized_receipt,
)
from trussted.db.session import transaction


def test_receipt_round_trip_retains_order_and_historical_public_key(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    with transaction(factory) as session:
        prepare_receipt(session)
        assert (
            save_finalized_receipt(
                session,
                receipt_bundle(),
                verify=accept_external_signature,
            )
            == "receipt"
        )
        revoke_signing_key(session, "key", revoked_at=NOW + timedelta(days=1))
    with factory() as session:
        detail = get_receipt(session, "receipt")
    assert detail.bundle == receipt_bundle()
    assert [event.seq for event in detail.bundle.events] == [0, 1]
    assert detail.signing_key.public_key == "public-bytes"
    assert detail.signing_key.revoked_at == NOW + timedelta(days=1)


@pytest.mark.parametrize("defect", ["empty", "gap", "first", "link", "payload", "final", "parent"])
def test_rejects_invalid_event_chain_before_any_write(
    factory: sessionmaker[Session],
    registry: None,
    defect: str,
) -> None:
    bundle = receipt_bundle()
    events = list(bundle.events)
    if defect == "empty":
        bundle = bundle.model_copy(update={"events": ()})
    elif defect == "final":
        bundle = bundle.model_copy(update={"final_hash": "d" * 64})
    else:
        changes: dict[str, dict[str, object]] = {
            "gap": {"seq": 2},
            "first": {"prev_hash": "d" * 64},
            "link": {"prev_hash": "d" * 64},
            "payload": {"payload_hash": "d" * 64},
            "parent": {"receipt_id": "other"},
        }
        index = 0 if defect == "first" else 1
        events[index] = events[index].model_copy(update=changes[defect])
        bundle = bundle.model_copy(update={"events": tuple(events)})
    with transaction(factory) as session:
        prepare_receipt(session)
    with pytest.raises(InvalidEvidence):
        with transaction(factory) as session:
            save_finalized_receipt(session, bundle, verify=accept_external_signature)
    with factory() as session:
        assert session.scalar(text("SELECT count(*) FROM receipts")) == 0
        assert session.scalar(text("SELECT count(*) FROM receipt_events")) == 0


def test_external_verifier_failure_prevents_persistence(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    def reject(bundle: object) -> None:
        raise InvalidEvidence("External signature verification rejected bundle")

    with transaction(factory) as session:
        prepare_receipt(session)
    with pytest.raises(InvalidEvidence):
        with transaction(factory) as session:
            save_finalized_receipt(session, receipt_bundle(), verify=reject)
    with factory() as session:
        assert session.scalar(text("SELECT count(*) FROM receipts")) == 0


def test_missing_key_and_duplicate_receipt_are_rejected(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    with transaction(factory) as session:
        prepare_receipt(session)
    with pytest.raises(InvalidEvidence):
        with transaction(factory) as session:
            save_finalized_receipt(
                session,
                receipt_bundle().model_copy(update={"signing_key_id": "missing"}),
                verify=accept_external_signature,
            )
    with transaction(factory) as session:
        save_finalized_receipt(session, receipt_bundle(), verify=accept_external_signature)
    with pytest.raises(DuplicateRecord):
        with transaction(factory) as session:
            original = receipt_bundle()
            save_finalized_receipt(
                session,
                original.model_copy(
                    update={
                        "id": "second",
                        "events": tuple(
                            event.model_copy(
                                update={
                                    "id": f"second-{event.id}",
                                    "receipt_id": "second",
                                }
                            )
                            for event in original.events
                        ),
                    }
                ),
                verify=accept_external_signature,
            )
    with factory() as session, pytest.raises(RecordNotFound):
        get_receipt(session, "missing")


def test_partial_receipt_failure_rolls_back_header_and_events(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    with transaction(factory) as session:
        prepare_receipt(session)
        session.execute(
            text(
                "CREATE TRIGGER reject_second_event BEFORE INSERT ON receipt_events "
                "WHEN NEW.seq = 1 BEGIN SELECT RAISE(ABORT, 'injected failure'); END"
            )
        )
    with pytest.raises(InvalidEvidence):
        with transaction(factory) as session:
            save_finalized_receipt(session, receipt_bundle(), verify=accept_external_signature)
    with factory() as session:
        assert session.scalar(text("SELECT count(*) FROM receipts")) == 0
        assert session.scalar(text("SELECT count(*) FROM receipt_events")) == 0
