"""Mock gateway which independently verifies and atomically redeems Warrant credentials."""

from __future__ import annotations

import hmac
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

import jwt

from warrant.credential.cart import Cart, cart_hash
from warrant.credential.keys import KeyRing
from warrant.credential.token import (
    CredentialConfig,
    CredentialLedger,
    RedemptionStatus,
    valid_claim_shape,
)


class RejectionCode(StrEnum):
    ACCEPTED = "ACCEPTED"
    MISSING_CREDENTIAL = "MISSING_CREDENTIAL"
    MALFORMED_CREDENTIAL = "MALFORMED_CREDENTIAL"
    UNKNOWN_KEY = "UNKNOWN_KEY"
    SIGNATURE_INVALID = "SIGNATURE_INVALID"
    CREDENTIAL_EXPIRED = "CREDENTIAL_EXPIRED"
    CART_MISMATCH = "CART_MISMATCH"
    MERCHANT_MISMATCH = "MERCHANT_MISMATCH"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    RUN_MISMATCH = "RUN_MISMATCH"
    CREDENTIAL_NOT_ISSUED = "CREDENTIAL_NOT_ISSUED"
    CREDENTIAL_REPLAYED = "CREDENTIAL_REPLAYED"
    CREDENTIAL_REVOKED = "CREDENTIAL_REVOKED"
    DATABASE_ERROR = "DATABASE_ERROR"


@dataclass(frozen=True, slots=True)
class GatewayResult:
    accepted: bool
    code: RejectionCode


class MockGateway:
    def __init__(
        self,
        *,
        config: CredentialConfig,
        key_ring: KeyRing,
        ledger: CredentialLedger,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._config = config
        self._keys = key_ring
        self._ledger = ledger
        self._clock = clock or (lambda: datetime.now(UTC))

    def authorize(
        self,
        *,
        token: str | None,
        cart: Cart,
        run_id: str,
    ) -> GatewayResult:
        if token is None or token == "":
            return GatewayResult(False, RejectionCode.MISSING_CREDENTIAL)
        if not isinstance(token, str) or len(token) > 8192:
            return GatewayResult(False, RejectionCode.MALFORMED_CREDENTIAL)
        instant = self._clock()
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("gateway clock must return an aware datetime")

        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError:
            return GatewayResult(False, RejectionCode.MALFORMED_CREDENTIAL)
        key_id = header.get("kid")
        if set(header) != {"alg", "kid", "typ"}:
            return GatewayResult(False, RejectionCode.MALFORMED_CREDENTIAL)
        if header.get("alg") != "EdDSA" or header.get("typ") != "JWT":
            return GatewayResult(False, RejectionCode.MALFORMED_CREDENTIAL)
        if not isinstance(key_id, str):
            return GatewayResult(False, RejectionCode.MALFORMED_CREDENTIAL)
        public_key = self._keys.get(key_id)
        if public_key is None:
            return GatewayResult(False, RejectionCode.UNKNOWN_KEY)

        try:
            claims = jwt.decode(
                token,
                public_key,
                algorithms=["EdDSA"],
                audience=self._config.audience,
                issuer=self._config.issuer,
                options={
                    "verify_exp": False,  # checked against the injected clock below
                    "verify_iat": False,  # checked against the same injected clock
                    "require": [
                        "iss",
                        "aud",
                        "exp",
                        "iat",
                        "jti",
                        "v",
                        "cart_hash",
                        "merchant_id",
                        "amount_minor",
                        "currency",
                        "run_id",
                    ],
                },
            )
        except jwt.InvalidSignatureError:
            return GatewayResult(False, RejectionCode.SIGNATURE_INVALID)
        except jwt.InvalidTokenError:
            return GatewayResult(False, RejectionCode.MALFORMED_CREDENTIAL)

        if not valid_claim_shape(claims):
            return GatewayResult(False, RejectionCode.MALFORMED_CREDENTIAL)
        instant_epoch = int(instant.timestamp())
        if claims["exp"] <= instant_epoch:
            return GatewayResult(False, RejectionCode.CREDENTIAL_EXPIRED)
        if claims["iat"] > instant_epoch or claims["exp"] <= claims["iat"]:
            return GatewayResult(False, RejectionCode.MALFORMED_CREDENTIAL)
        if claims["run_id"] != run_id:
            return GatewayResult(False, RejectionCode.RUN_MISMATCH)

        try:
            submitted_cart_hash = cart_hash(cart)
        except (TypeError, ValueError):
            return GatewayResult(False, RejectionCode.CART_MISMATCH)
        if claims["merchant_id"] != cart.merchant_id:
            return GatewayResult(False, RejectionCode.MERCHANT_MISMATCH)
        if claims["amount_minor"] != cart.amount_minor:
            return GatewayResult(False, RejectionCode.AMOUNT_MISMATCH)
        if claims["currency"] != cart.currency:
            return GatewayResult(False, RejectionCode.CURRENCY_MISMATCH)
        if not hmac.compare_digest(claims["cart_hash"], submitted_cart_hash):
            return GatewayResult(False, RejectionCode.CART_MISMATCH)

        try:
            status = self._ledger.redeem_once(
                nonce=claims["jti"],
                run_id=run_id,
                signature=token.rsplit(".", 1)[1],
                approval_hash=claims["approval_hash"],
                cart_hash=submitted_cart_hash,
                merchant_id=cart.merchant_id,
                amount_minor=cart.amount_minor,
                currency=cart.currency,
                now=instant,
            )
        except Exception:
            # An injected database adapter must not turn an operational failure into
            # an exception containing private driver details at the gateway boundary.
            return GatewayResult(False, RejectionCode.DATABASE_ERROR)
        return _result_for(status)


def _result_for(status: RedemptionStatus) -> GatewayResult:
    mapping = {
        RedemptionStatus.REDEEMED: GatewayResult(True, RejectionCode.ACCEPTED),
        RedemptionStatus.REJECTED: GatewayResult(False, RejectionCode.CREDENTIAL_NOT_ISSUED),
        RedemptionStatus.NOT_FOUND: GatewayResult(False, RejectionCode.CREDENTIAL_NOT_ISSUED),
        RedemptionStatus.REPLAYED: GatewayResult(False, RejectionCode.CREDENTIAL_REPLAYED),
        RedemptionStatus.MISMATCH: GatewayResult(False, RejectionCode.CREDENTIAL_NOT_ISSUED),
        RedemptionStatus.DECISION_REVOKED: GatewayResult(False, RejectionCode.CREDENTIAL_REVOKED),
        RedemptionStatus.EXPIRED: GatewayResult(False, RejectionCode.CREDENTIAL_EXPIRED),
    }
    return mapping[status]
