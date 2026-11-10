"""ALLOW-gated simulated issuance and atomic single-use nonce consumption."""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from trussted.db.contracts.credentials import CredentialInput
from trussted.db.errors import InvalidEvidence, flush, storage_errors
from trussted.db.repositories.runs import require_run
from trussted.db.tables.credentials import CredentialRow
from trussted.db.tables.outcomes import DecisionRow
from trussted.db.values import utc_datetime, utc_text


def store_credential(session: Session, value: CredentialInput, *, now: datetime) -> str:
    """Store upstream-verified token fields after matching current ALLOW evidence."""
    if value.expires_at <= utc_datetime(now):
        raise InvalidEvidence("Credential must expire after the injected current time")
    run = require_run(session, value.run_id)
    decision = session.scalar(select(DecisionRow).where(DecisionRow.run_id == value.run_id))
    if (
        run.status in {"error", "timeout"}
        or decision is None
        or decision.result != "ALLOW"
        or decision.amount_minor != value.amount_minor
        or decision.currency != value.currency
    ):
        raise InvalidEvidence("Credential requires matching same-run ALLOW evidence")
    session.add(
        CredentialRow(
            id=value.id,
            run_id=value.run_id,
            cart_hash=value.cart_hash,
            merchant_id=value.merchant_id,
            amount_minor=value.amount_minor,
            currency=value.currency,
            nonce=value.nonce,
            expires_at=utc_text(value.expires_at),
            redeemed_at=None,
            signature=value.signature,
        )
    )
    flush(session)
    return value.id


def redeem_credential(session: Session, *, nonce: str, now: datetime) -> bool:
    """Consume once with one UPDATE as the first operation in a fresh transaction.

    Caller verifies signature/cart/merchant/amount before this call and commits its
    transaction before treating True as consumed. Storage failures propagate.
    """
    timestamp = utc_text(now)
    with storage_errors():
        redeemed = session.execute(
            update(CredentialRow)
            .where(
                CredentialRow.nonce == nonce,
                CredentialRow.redeemed_at.is_(None),
                CredentialRow.expires_at > timestamp,
            )
            .values(redeemed_at=timestamp)
            .returning(CredentialRow.id)
            .execution_options(
                synchronize_session=False,
                autoflush=False,
            )
        ).scalar_one_or_none()
    return redeemed is not None
