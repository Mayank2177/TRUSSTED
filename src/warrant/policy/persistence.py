"""Persist deterministic policy decisions through warrant.db's repository boundary."""

from uuid import uuid4

from sqlalchemy.orm import Session

from warrant.db.contracts.outcomes import DecisionInput
from warrant.db.repositories.outcomes import save_decision
from warrant.policy.models import Decision


def persist_decision(session: Session, decision: Decision) -> str:
    """Write an evaluated decision with its exact winner and approval fingerprint.

    The caller owns the transaction. The shared repository verifies same-run fact
    ownership and rolls back with that transaction if any invariant fails.
    """
    if type(decision.amount_minor) is not int or decision.amount_minor < 0:
        raise ValueError("persisted policy decision requires trusted integer amount_minor")
    if not isinstance(decision.currency, str):
        raise ValueError("persisted policy decision requires trusted currency")
    value = DecisionInput(
        id=uuid4().hex,
        run_id=decision.run_id,
        result=decision.result.value,
        reasons=tuple(reason.value for reason in decision.reasons),
        policy_version=decision.policy_version,
        amount_minor=decision.amount_minor,
        currency=decision.currency,
        winner_fact_id=decision.winner_fact_id,
        approval_hash=decision.approval_hash,
    )
    return save_decision(session, value)
