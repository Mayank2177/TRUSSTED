"""Simulated credentials need matching ALLOW evidence and single-use consumption."""

from datetime import timedelta
from typing import Literal

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session, sessionmaker

from tests.db.conftest import NOW
from tests.db.test_evidence import fact, observation
from tests.db.test_runs import start
from warrant.db.contracts.credentials import CredentialInput
from warrant.db.contracts.outcomes import DecisionInput
from warrant.db.contracts.runs import RunFinish
from warrant.db.errors import DuplicateRecord, InvalidEvidence
from warrant.db.repositories.credentials import redeem_credential, store_credential
from warrant.db.repositories.evidence import save_observations, save_product_facts
from warrant.db.repositories.outcomes import save_decision
from warrant.db.repositories.runs import create_run, finish_run
from warrant.db.session import transaction
from warrant.db.tables.evidence import ProductFactRow


def redeem(
    session: Session,
    *,
    nonce: str = "nonce",
    now=NOW,
    run_id: str = "run",
    signature: str = "external-signature",
    approval_hash: str = "a" * 64,
    cart_hash: str = "a" * 64,
    merchant_id: str = "merchant",
    amount_minor: int = 100,
    currency: str = "USD",
) -> bool:
    return redeem_credential(
        session,
        nonce=nonce,
        run_id=run_id,
        signature=signature,
        approval_hash=approval_hash,
        cart_hash=cart_hash,
        merchant_id=merchant_id,
        amount_minor=amount_minor,
        currency=currency,
        now=now,
    )


def credential() -> CredentialInput:
    return CredentialInput(
        id="credential",
        run_id="run",
        cart_hash="a" * 64,
        merchant_id="merchant",
        amount_minor=100,
        currency="USD",
        nonce="nonce",
        expires_at=NOW + timedelta(minutes=5),
        signature="external-signature",
        approval_hash="a" * 64,
    )


def allow_decision(
    session: Session, result: Literal["ALLOW", "STEP_UP", "BLOCK"] = "ALLOW"
) -> None:
    if session.get(ProductFactRow, "fact") is None:
        save_observations(session, (observation(),))
        save_product_facts(session, (fact(),))
    save_decision(
        session,
        DecisionInput(
            id="decision",
            run_id="run",
            result=result,
            reasons=("synthetic_reason",),
            policy_version="1",
            amount_minor=100,
            currency="USD",
            winner_fact_id="fact",
            approval_hash="a" * 64,
        ),
    )


@pytest.mark.parametrize("decision", ["missing", "STEP_UP", "BLOCK"])
def test_issuance_requires_same_run_allow_decision(
    factory: sessionmaker[Session],
    registry: None,
    decision: Literal["missing", "STEP_UP", "BLOCK"],
) -> None:
    with transaction(factory) as session:
        create_run(session, start())
        if decision != "missing":
            allow_decision(session, decision)
    with pytest.raises(InvalidEvidence):
        with transaction(factory) as session:
            store_credential(session, credential(), now=NOW)


@pytest.mark.parametrize("mismatch", ["amount", "currency", "run", "expired", "boundary"])
def test_issuance_rejects_mismatched_or_expired_credentials(
    factory: sessionmaker[Session],
    registry: None,
    mismatch: str,
) -> None:
    with transaction(factory) as session:
        create_run(session, start())
        create_run(session, start("other", repetition=2))
        allow_decision(session)
    changes: dict[str, dict[str, object]] = {
        "amount": {"amount_minor": 101},
        "currency": {"currency": "INR"},
        "run": {"run_id": "other"},
        "expired": {"expires_at": NOW - timedelta(seconds=1)},
        "boundary": {"expires_at": NOW},
    }
    with pytest.raises(InvalidEvidence):
        with transaction(factory) as session:
            store_credential(session, credential().model_copy(update=changes[mismatch]), now=NOW)


@pytest.mark.parametrize("status", ["error", "timeout"])
def test_failed_runs_cannot_issue_credentials(
    factory: sessionmaker[Session],
    registry: None,
    status: Literal["error", "timeout"],
) -> None:
    with transaction(factory) as session:
        create_run(session, start())
        allow_decision(session)
        finish_run(session, "run", RunFinish(status=status, finished_at=NOW))
    with pytest.raises(InvalidEvidence):
        with transaction(factory) as session:
            store_credential(session, credential(), now=NOW)


def test_credential_duplicate_nonce_is_rejected(
    factory: sessionmaker[Session], registry: None
) -> None:
    with transaction(factory) as session:
        create_run(session, start())
        allow_decision(session)
        assert store_credential(session, credential(), now=NOW) == "credential"
    with pytest.raises(DuplicateRecord):
        with transaction(factory) as session:
            store_credential(
                session,
                credential().model_copy(update={"id": "second"}),
                now=NOW,
            )


def test_credential_unique_run_constraint_rejects_distinct_nonce(
    factory: sessionmaker[Session], registry: None
) -> None:
    with transaction(factory) as session:
        create_run(session, start())
        allow_decision(session)
        store_credential(session, credential(), now=NOW)
    with pytest.raises(DuplicateRecord):
        with transaction(factory) as session:
            store_credential(
                session,
                credential().model_copy(update={"id": "second", "nonce": "different-nonce"}),
                now=NOW,
            )


def test_redemption_is_first_operation_and_replay_fails(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    with transaction(factory) as session:
        create_run(session, start())
        allow_decision(session)
        store_credential(session, credential(), now=NOW)
    statements: list[str] = []

    def capture(
        connection: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        statements.append(statement)

    engine = factory.kw["bind"]
    event.listen(engine, "before_cursor_execute", capture)
    try:
        with transaction(factory) as session:
            assert redeem(session) is True
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert len(statements) == 1
    assert statements[0].lstrip().upper().startswith("UPDATE ")
    with transaction(factory) as session:
        assert redeem(session) is False
        assert redeem(session, nonce="unknown") is False
    with factory() as session:
        assert (
            session.scalar(text("SELECT redeemed_at FROM credentials"))
            == "2026-01-01T00:00:00.000000Z"
        )


def test_redemption_exact_expiry_is_expired(
    factory: sessionmaker[Session],
    registry: None,
) -> None:
    with transaction(factory) as session:
        create_run(session, start())
        allow_decision(session)
        store_credential(session, credential(), now=NOW)
    with transaction(factory) as session:
        assert redeem(session, now=NOW + timedelta(minutes=5)) is False


@pytest.mark.parametrize(
    "mismatch",
    [
        {"run_id": "other"},
        {"signature": "different-signature"},
        {"approval_hash": "b" * 64},
        {"cart_hash": "b" * 64},
        {"merchant_id": "other-merchant"},
        {"amount_minor": 101},
        {"currency": "INR"},
    ],
)
def test_redemption_requires_all_signed_fields_to_match_persisted_row(
    factory: sessionmaker[Session],
    registry: None,
    mismatch: dict[str, object],
) -> None:
    with transaction(factory) as session:
        create_run(session, start())
        allow_decision(session)
        store_credential(session, credential(), now=NOW)
    with transaction(factory) as session:
        assert redeem(session, **mismatch) is False
        assert redeem(session) is True
