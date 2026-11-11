"""Credential persistence adapter backed only by the shared warrant.db repositories."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from warrant.credential.token import (
    CredentialAlreadyIssued,
    CredentialLedger,
    CredentialStoreError,
    IssuedCredential,
    RedemptionStatus,
)
from warrant.policy.models import Decision, DecisionResult


class SharedCredentialLedger(CredentialLedger):
    """Use Ayush's canonical repositories and transaction helper for all writes."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._factory = factory
        self._clock = clock or (lambda: datetime.now(UTC))

    def create_after_allow(self, *, decision: Decision, credential: IssuedCredential) -> None:
        """Atomically persist the exact ALLOW provenance and signed credential record."""
        from warrant.db.contracts.credentials import CredentialInput
        from warrant.db.contracts.outcomes import DecisionInput
        from warrant.db.errors import DuplicateRecord
        from warrant.db.repositories.credentials import store_credential
        from warrant.db.repositories.outcomes import save_decision
        from warrant.db.session import transaction

        if decision.result is not DecisionResult.ALLOW:
            raise CredentialStoreError("credential persistence requires ALLOW")
        if (
            not decision.winner_fact_id
            or not decision.approval_hash
            or credential.approval_hash != decision.approval_hash
            or credential.run_id != decision.run_id
            or type(decision.amount_minor) is not int
            or decision.amount_minor < 0
            or not isinstance(decision.currency, str)
            or re.fullmatch(r"[A-Z]{3}", decision.currency) is None
        ):
            raise CredentialStoreError("credential is missing matching product approval provenance")
        decision_input = DecisionInput(
            id=uuid4().hex,
            run_id=decision.run_id,
            result="ALLOW",
            reasons=tuple(reason.value for reason in decision.reasons),
            policy_version=decision.policy_version,
            amount_minor=decision.amount_minor,
            currency=decision.currency,
            winner_fact_id=decision.winner_fact_id,
            approval_hash=decision.approval_hash,
        )
        credential_input = CredentialInput(
            id=credential.credential_id,
            run_id=credential.run_id,
            cart_hash=credential.cart_hash,
            merchant_id=credential.merchant_id,
            amount_minor=credential.amount_minor,
            currency=credential.currency,
            nonce=credential.nonce,
            expires_at=credential.expires_at,
            signature=credential.signature,
            approval_hash=credential.approval_hash,
        )
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise CredentialStoreError("credential persistence clock must be timezone-aware")
        with transaction(self._factory) as session:
            try:
                save_decision(session, decision_input)
            except DuplicateRecord as error:
                raise CredentialStoreError(
                    "a decision already exists for this run; atomic issuance was rejected"
                ) from error
            try:
                store_credential(session, credential_input, now=now)
            except DuplicateRecord as error:
                raise CredentialAlreadyIssued("a credential already exists for this run") from error

    def redeem_once(
        self,
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
    ) -> RedemptionStatus:
        """Consume in a fresh transaction; the repository UPDATE is the first DB operation.

        The gateway validates the token and cart first. All signed authorization values are
        repeated in the database compare-and-set to detect a mismatched or altered stored row.
        """
        from warrant.db.repositories.credentials import redeem_credential
        from warrant.db.session import transaction

        with transaction(self._factory) as session:
            redeemed = redeem_credential(
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
        return RedemptionStatus.REDEEMED if redeemed else RedemptionStatus.REJECTED
