"""Store verified, completed receipts atomically; expose no event append operation."""

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from warrant.db.contracts.receipts import (
    FinalizedReceipt,
    ReceiptDetail,
    ReceiptEventInput,
    ReceiptVerifier,
    SigningKeyInput,
)
from warrant.db.errors import InvalidEvidence, InvalidTransition, RecordNotFound, flush
from warrant.db.repositories.runs import require_run
from warrant.db.tables.receipts import ReceiptEventRow, ReceiptRow, SigningKeyRow
from warrant.db.values import canonical_json, sha256_hex, utc_text


def register_signing_key(session: Session, value: SigningKeyInput) -> str:
    """Register public bytes once; conflicting identities are typed storage errors."""
    if value.revoked_at is not None and value.revoked_at < value.created_at:
        raise InvalidEvidence("Key cannot be revoked before creation")
    session.add(
        SigningKeyRow(
            id=value.id,
            algorithm=value.algorithm,
            public_key=value.public_key,
            created_at=utc_text(value.created_at),
            revoked_at=utc_text(value.revoked_at) if value.revoked_at is not None else None,
        )
    )
    flush(session)
    return value.id


def revoke_signing_key(session: Session, key_id: str, *, revoked_at: datetime) -> None:
    """Retain historical public bytes and record a single revocation time."""
    row = session.get(SigningKeyRow, key_id)
    if row is None:
        raise RecordNotFound("Signing key does not exist")
    timestamp = utc_text(revoked_at)
    if timestamp < row.created_at:
        raise InvalidEvidence("Key cannot be revoked before creation")
    if row.revoked_at is not None and row.revoked_at != timestamp:
        raise InvalidTransition("Signing key was already revoked")
    row.revoked_at = timestamp
    flush(session)


def _validate_chain(bundle: FinalizedReceipt) -> tuple[str, ...]:
    if not bundle.events:
        raise InvalidEvidence("A finalized receipt must contain events")
    previous = "0" * 64
    payloads: list[str] = []
    for sequence, event in enumerate(bundle.events):
        if event.receipt_id != bundle.id or event.seq != sequence or event.prev_hash != previous:
            raise InvalidEvidence("Receipt events must form one contiguous linked chain")
        try:
            payload = canonical_json(event.payload)
        except (ValueError, TypeError) as error:
            raise InvalidEvidence("Receipt payload is not canonicalizable JSON") from error
        if sha256_hex(payload.encode("utf-8")) != event.payload_hash:
            raise InvalidEvidence("Receipt payload hash does not match its canonical bytes")
        payloads.append(payload)
        previous = event.event_hash
    if previous != bundle.final_hash:
        raise InvalidEvidence("Final receipt hash does not match its last event")
    return tuple(payloads)


def save_finalized_receipt(
    session: Session,
    value: FinalizedReceipt,
    *,
    verify: ReceiptVerifier,
) -> str:
    """Verify before writes, then flush header and events in the caller's transaction.

    The injected verifier owns real signature and canonical event-envelope checks.
    A failed flush must escape the transaction context so its owner rolls back.
    """
    payloads = _validate_chain(value)
    verify(value)
    require_run(session, value.run_id)
    key = session.get(SigningKeyRow, value.signing_key_id)
    if key is None:
        raise InvalidEvidence("Receipt signing key does not exist")
    timestamp = utc_text(value.created_at)
    if timestamp < key.created_at or (key.revoked_at is not None and timestamp >= key.revoked_at):
        raise InvalidEvidence("Signing key was not valid at receipt creation")
    session.add(
        ReceiptRow(
            id=value.id,
            run_id=value.run_id,
            final_hash=value.final_hash,
            signature=value.signature,
            signing_key_id=value.signing_key_id,
            created_at=timestamp,
            export_path=value.export_path,
        )
    )
    flush(session)
    for event, payload in zip(value.events, payloads, strict=True):
        session.add(
            ReceiptEventRow(
                id=event.id,
                receipt_id=value.id,
                seq=event.seq,
                type=event.type,
                payload=payload,
                payload_hash=event.payload_hash,
                prev_hash=event.prev_hash,
                event_hash=event.event_hash,
                created_at=utc_text(event.created_at),
            )
        )
    flush(session)
    return value.id


def get_receipt(session: Session, receipt_id: str) -> ReceiptDetail:
    """Load a detached complete bundle in sequence order with retained key metadata."""
    row = session.get(ReceiptRow, receipt_id)
    if row is None:
        raise RecordNotFound("Receipt does not exist")
    key = session.get(SigningKeyRow, row.signing_key_id)
    assert key is not None
    events = session.scalars(
        select(ReceiptEventRow)
        .where(
            ReceiptEventRow.receipt_id == receipt_id,
        )
        .order_by(ReceiptEventRow.seq)
    )
    bundle = FinalizedReceipt.model_validate(
        {
            **{column.name: getattr(row, column.name) for column in ReceiptRow.__table__.columns},
            "events": tuple(
                ReceiptEventInput.model_validate(
                    {
                        **{
                            column.name: getattr(event, column.name)
                            for column in ReceiptEventRow.__table__.columns
                        },
                        "payload": json.loads(event.payload),
                    }
                )
                for event in events
            ),
        }
    )
    return ReceiptDetail(bundle=bundle, signing_key=SigningKeyInput.model_validate(key))
