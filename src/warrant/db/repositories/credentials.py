"""ALLOW-gated simulated issuance and atomic single-use nonce consumption."""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from warrant.db.contracts.credentials import CredentialInput
from warrant.db.errors import InvalidEvidence, flush, storage_errors
from warrant.db.repositories.runs import require_run
from warrant.db.tables.credentials import CredentialRow
from warrant.db.tables.evidence import ProductFactRow
from warrant.db.tables.outcomes import DecisionRow
from warrant.db.values import utc_datetime, utc_text


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
        or decision.winner_fact_id is None
        or decision.approval_hash is None
        or decision.approval_hash != value.approval_hash
    ):
        raise InvalidEvidence("Credential requires matching same-run ALLOW evidence")
    winner = session.get(ProductFactRow, decision.winner_fact_id)
    if winner is None or winner.run_id != value.run_id:
        raise InvalidEvidence("Credential ALLOW decision has no same-run winning fact")
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
            approval_hash=value.approval_hash,
        )
    )
    flush(session)
    return value.id


def redeem_credential(
    session: Session,
    *,
    nonce: str,
    run_id: str,
    signature: str,
    approval_hash: str,
    cart_hash: str,
    merchant_id: str,
    amount_minor: int,
    currency: str,
    now: datetime,
) -> bool:
    """Consume once with one UPDATE as the first operation in a fresh transaction.

    Caller verifies signature/cart/merchant/amount before this call and commits its
    transaction before treating True as consumed. Every signed and persisted authorization
    field is part of the same compare-and-set predicate, so a matching nonce cannot redeem a
    row whose run, signature, approval, cart, merchant, amount, or currency was altered.
    Storage failures propagate.
    """
    timestamp = utc_text(now)
    with storage_errors():
        redeemed = session.execute(
            update(CredentialRow)
            .where(
                CredentialRow.nonce == nonce,
                CredentialRow.run_id == run_id,
                CredentialRow.redeemed_at.is_(None),
                CredentialRow.expires_at > timestamp,
                CredentialRow.signature == signature,
                CredentialRow.approval_hash == approval_hash,
                CredentialRow.cart_hash == cart_hash,
                CredentialRow.merchant_id == merchant_id,
                CredentialRow.amount_minor == amount_minor,
                CredentialRow.currency == currency,
            )
            .values(redeemed_at=timestamp)
            .returning(CredentialRow.id)
            .execution_options(
                synchronize_session=False,
                autoflush=False,
            )
        ).scalar_one_or_none()
    return redeemed is not None
