"""Warrant credential issuance using compact JWT/JWS and the EdDSA algorithm."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from warrant.credential.cart import Cart
from warrant.credential.keys import SigningKey
from warrant.policy.models import Decision, DecisionResult

_CURRENCY = re.compile(r"[A-Z]{3}\Z")


class CredentialError(RuntimeError):
    """Safe-to-report credential operation failure."""


class CredentialIssuanceDenied(CredentialError):
    """Issuance is unsafe because authorization or cart binding evidence is missing."""


class CredentialStoreError(CredentialError):
    """Credential persistence failed; no credential may be returned as usable."""


class CredentialAlreadyIssued(CredentialStoreError):
    """This run already has a persisted credential and cannot issue another."""


class RedemptionStatus(StrEnum):
    REDEEMED = "REDEEMED"
    REJECTED = "REJECTED"
    NOT_FOUND = "NOT_FOUND"
    REPLAYED = "REPLAYED"
    MISMATCH = "MISMATCH"
    DECISION_REVOKED = "DECISION_REVOKED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True, slots=True)
class CredentialConfig:
    issuer: str
    audience: str = "warrant-mock-gateway"
    ttl_seconds: int = 300

    def __post_init__(self) -> None:
        if not self.issuer.strip() or not self.audience.strip():
            raise ValueError("credential issuer and audience must be non-empty")
        if type(self.ttl_seconds) is not int or not 1 <= self.ttl_seconds <= 3600:
            raise ValueError("credential lifetime must be between 1 and 3600 seconds")


@dataclass(frozen=True, slots=True)
class IssuedCredential:
    credential_id: str
    run_id: str
    token: str
    signature: str
    cart_hash: str
    merchant_id: str
    amount_minor: int
    currency: str
    nonce: str
    expires_at: datetime
    key_id: str
    approval_hash: str = ""
    issued_at: datetime | None = None


class CredentialLedger(Protocol):
    """Narrow persistence contract; the database owner supplies the configured adapter."""

    def create_after_allow(self, *, decision: Decision, credential: IssuedCredential) -> None: ...

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
    ) -> RedemptionStatus: ...


def issue_credential(
    *,
    decision: Decision,
    cart: Cart,
    signing_key: SigningKey,
    config: CredentialConfig,
    ledger: CredentialLedger,
    now: datetime | None = None,
) -> IssuedCredential:
    """Fail closed until the decision proves which selected product the cart contains."""
    if decision.result is not DecisionResult.ALLOW:
        raise CredentialIssuanceDenied("purchase credential requires an ALLOW decision")
    if decision.amount_minor != cart.amount_minor or decision.currency != cart.currency:
        raise CredentialIssuanceDenied("decision amount or currency does not match cart")
    # Decision carries no authoritative winner/product-to-cart binding. Amount and
    # currency alone cannot prove that this cart contains the selected product.
    raise CredentialIssuanceDenied(
        "decision does not contain a verified selected-product-to-cart binding"
    )


def valid_claim_shape(claims: object) -> bool:
    if not isinstance(claims, dict):
        return False
    string_fields = (
        "iss",
        "aud",
        "jti",
        "cart_hash",
        "merchant_id",
        "currency",
        "run_id",
        "approval_hash",
    )
    if any(not isinstance(claims.get(field), str) or not claims[field] for field in string_fields):
        return False
    if _CURRENCY.fullmatch(claims["currency"]) is None:
        return False
    if re.fullmatch(r"[0-9a-f]{64}", claims["approval_hash"]) is None:
        return False
    for field in ("amount_minor", "exp", "iat"):
        if type(claims.get(field)) is not int:
            return False
    if claims["amount_minor"] < 0 or claims["exp"] <= 0 or claims["iat"] < 0:
        return False
    return type(claims.get("v")) is int and claims["v"] == 1
