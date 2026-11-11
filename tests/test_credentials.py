from __future__ import annotations

import base64
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Barrier

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError

from tests.support.sqlite_credential_ledger import SQLiteCredentialLedger
from warrant.credential.cart import Cart, CartLine, canonical_cart_bytes, cart_hash
from warrant.credential.gateway import MockGateway, RejectionCode
from warrant.credential.keys import (
    KeyConfigurationError,
    KeyRing,
    SigningKey,
    VerificationKey,
    generate_key_pair,
    load_signing_key,
    load_verification_key,
)
from warrant.credential.token import (
    CredentialAlreadyIssued,
    CredentialConfig,
    CredentialIssuanceDenied,
    IssuedCredential,
    issue_credential,
)
from warrant.policy.models import Decision, DecisionResult, ReasonCode

NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
APPROVAL_HASH = "a" * 64
CONFIG = CredentialConfig("warrant-test")


def make_cart(
    *,
    merchant: str = "fictional-merchant-a",
    currency: str = "INR",
    product: str = "fictional-ssd-1tb",
    tax: int = 500,
) -> Cart:
    return Cart(
        merchant_id=merchant,
        amount_minor=20_000 + tax,
        currency=currency,
        items=(CartLine(product, 2, 10_000, "SSD-1T-A"),),
        tax_minor=tax,
    )


def allow_decision(cart: Cart, *, result: DecisionResult = DecisionResult.ALLOW) -> Decision:
    return Decision(
        "run-1",
        result,
        (ReasonCode.CHECKS_PASSED,),
        "policy-test-1",
        cart.amount_minor,
        cart.currency,
        "fact-1",
        APPROVAL_HASH,
    )


def create_schema(path) -> None:
    # Test-only DDL mirrors the documented columns; it is not a project migration/schema owner.
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys=ON;
            CREATE TABLE runs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'running'
                    CHECK(status IN ('running','completed','error','timeout'))
            );
            CREATE TABLE decisions (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL UNIQUE REFERENCES runs(id),
                result TEXT NOT NULL CHECK(result IN ('ALLOW','STEP_UP','BLOCK')),
                reasons TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                amount_minor INTEGER NOT NULL,
                currency TEXT NOT NULL
            );
            CREATE TABLE credentials (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(id),
                cart_hash TEXT NOT NULL,
                merchant_id TEXT NOT NULL,
                amount_minor INTEGER NOT NULL,
                currency TEXT NOT NULL,
                nonce TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                redeemed_at TEXT,
                signature TEXT NOT NULL,
                approval_hash TEXT NOT NULL
            );
            INSERT INTO runs (id, status) VALUES ('run-1', 'running');
            """
        )


@pytest.fixture
def system(tmp_path):
    database = tmp_path / "warrant-test.sqlite3"
    create_schema(database)
    ledger = SQLiteCredentialLedger(database)
    private = Ed25519PrivateKey.generate()
    signing = SigningKey("test-key-1", private)
    public = VerificationKey("test-key-1", private.public_key())
    ring = KeyRing((public,))
    try:
        yield database, ledger, signing, ring
    finally:
        # Close the adapter-owned SQLite engine before pytest removes tmp_path;
        # Windows refuses to delete a database while SQLAlchemy still holds it.
        ledger.close()


def credential_fixture(
    system,
    cart: Cart,
    *,
    run_id: str = "run-1",
    config: CredentialConfig = CONFIG,
) -> tuple[Decision, IssuedCredential]:
    """Build a test-only signed credential without using the intentionally blocked issuer."""
    _, _, signing, _ = system
    decision = Decision(
        run_id,
        DecisionResult.ALLOW,
        (ReasonCode.CHECKS_PASSED,),
        "policy-test-1",
        cart.amount_minor,
        cart.currency,
        "fact-1",
        APPROVAL_HASH,
    )
    nonce = f"fixture-{decision.run_id}"
    issued_at = int(NOW.timestamp())
    expires_at = NOW + timedelta(seconds=config.ttl_seconds)
    payload = {
        "amount_minor": cart.amount_minor,
        "approval_hash": APPROVAL_HASH,
        "aud": config.audience,
        "cart_hash": cart_hash(cart),
        "currency": cart.currency,
        "exp": int(expires_at.timestamp()),
        "iat": issued_at,
        "iss": config.issuer,
        "jti": nonce,
        "merchant_id": cart.merchant_id,
        "run_id": decision.run_id,
        "v": 1,
    }
    token = jwt.encode(
        payload,
        signing.private_key,
        algorithm="EdDSA",
        headers={"kid": signing.key_id, "typ": "JWT"},
    )
    credential = IssuedCredential(
        credential_id=f"credential-{decision.run_id}",
        run_id=decision.run_id,
        token=token,
        signature=token.rsplit(".", 1)[1],
        cart_hash=cart_hash(cart),
        merchant_id=cart.merchant_id,
        amount_minor=cart.amount_minor,
        currency=cart.currency,
        nonce=nonce,
        expires_at=expires_at,
        key_id=signing.key_id,
        approval_hash=APPROVAL_HASH,
        issued_at=NOW,
    )
    return decision, credential


def issue(
    system,
    cart: Cart | None = None,
    *,
    run_id: str = "run-1",
    config: CredentialConfig = CONFIG,
    ledger=None,
):
    _, system_ledger, _, _ = system
    ledger = ledger or system_ledger
    cart = cart or make_cart()
    decision, credential = credential_fixture(system, cart, run_id=run_id, config=config)
    with sqlite3.connect(system[0]) as connection:
        connection.execute(
            "INSERT OR REPLACE INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "decision-1",
                run_id,
                "ALLOW",
                '["CHECKS_PASSED"]',
                "policy-test-1",
                cart.amount_minor,
                cart.currency,
            ),
        )
    ledger.create_after_allow(decision=decision, credential=credential)
    return credential


def test_ledger_stores_first_credential_for_run(system) -> None:
    credential = issue(system)
    with sqlite3.connect(system[0]) as connection:
        rows = connection.execute(
            "SELECT run_id, nonce FROM credentials WHERE run_id = ?", ("run-1",)
        ).fetchall()
    assert credential.nonce == rows[0][1]
    assert len(rows) == 1


def test_ledger_rejects_second_credential_for_run(system) -> None:
    issue(system)
    with pytest.raises(CredentialAlreadyIssued) as error:
        issue(system)
    assert "already been issued" in str(error.value)
    assert "database" not in str(error.value).lower()
    with sqlite3.connect(system[0]) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM credentials WHERE run_id = ?", ("run-1",)
            ).fetchone()[0]
            == 1
        )


def test_ledger_concurrent_create_for_one_run_commits_exactly_one_credential(system) -> None:
    cart = make_cart()
    decision = allow_decision(cart)
    with sqlite3.connect(system[0]) as connection:
        connection.execute(
            "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "decision-1",
                decision.run_id,
                decision.result.value,
                '["CHECKS_PASSED"]',
                decision.policy_version,
                decision.amount_minor,
                decision.currency,
            ),
        )

    attempt_count = 8
    start = Barrier(attempt_count)

    def attempt_issuance() -> str:
        start.wait(timeout=10)
        try:
            issue(system, cart)
            return "issued"
        except CredentialAlreadyIssued:
            return "already-issued"

    with ThreadPoolExecutor(max_workers=attempt_count) as executor:
        outcomes = list(executor.map(lambda _: attempt_issuance(), range(attempt_count)))

    assert outcomes.count("issued") == 1
    assert outcomes.count("already-issued") == attempt_count - 1
    with sqlite3.connect(system[0]) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM credentials WHERE run_id = ?", (decision.run_id,)
            ).fetchone()[0]
            == 1
        )


def test_ledger_rejects_credential_run_id_different_from_decision(system) -> None:
    credential = issue(system)
    with sqlite3.connect(system[0]) as connection:
        connection.execute("INSERT INTO runs (id) VALUES ('run-2')")
        connection.execute("DELETE FROM credentials WHERE run_id = 'run-1'")

    with pytest.raises(ValueError, match="run ID does not match"):
        system[1].create_after_allow(
            decision=allow_decision(make_cart()),
            credential=replace(credential, run_id="run-2"),
        )
    with sqlite3.connect(system[0]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM credentials").fetchone()[0] == 0


def test_ledger_allows_one_credential_for_each_distinct_run(system) -> None:
    cart = make_cart()
    issue(system, cart)
    decision = Decision(
        "run-2",
        DecisionResult.ALLOW,
        (ReasonCode.CHECKS_PASSED,),
        "policy-test-1",
        cart.amount_minor,
        cart.currency,
    )
    with sqlite3.connect(system[0]) as connection:
        connection.execute("INSERT INTO runs (id) VALUES (?)", (decision.run_id,))
        connection.execute(
            "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "decision-2",
                decision.run_id,
                decision.result.value,
                '["CHECKS_PASSED"]',
                decision.policy_version,
                decision.amount_minor,
                decision.currency,
            ),
        )

    issued = issue(system, cart, run_id=decision.run_id)
    with sqlite3.connect(system[0]) as connection:
        rows = connection.execute("SELECT run_id FROM credentials ORDER BY run_id").fetchall()
    assert issued.token
    assert rows == [("run-1",), ("run-2",)]


def test_failed_credential_insert_rolls_back_and_leaves_no_partial_row(system) -> None:
    cart = make_cart()
    with sqlite3.connect(system[0]) as connection:
        connection.execute(
            """CREATE TRIGGER reject_credential_insert
               BEFORE INSERT ON credentials
               BEGIN SELECT RAISE(ABORT, 'private trigger detail'); END"""
        )

    with pytest.raises(Exception, match="private trigger detail"):
        issue(system, cart)
    with sqlite3.connect(system[0]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM credentials").fetchone()[0] == 0
        connection.execute("DROP TRIGGER reject_credential_insert")

    issue(system, cart)
    with sqlite3.connect(system[0]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM credentials").fetchone()[0] == 1


class _TestClock:
    def __init__(self, value: datetime = NOW) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


class RunBoundGateway:
    """Test adapter supplies the simulated API's current run context explicitly."""

    def __init__(self, service: MockGateway, clock: _TestClock) -> None:
        self.service = service
        self.clock = clock

    def authorize(self, *, token, cart, now=None):
        if now is not None:
            self.clock.value = now
        return self.service.authorize(token=token, cart=cart, run_id="run-1")


def gateway(system, *, config: CredentialConfig = CONFIG, ledger=None) -> RunBoundGateway:
    _, default_ledger, _, ring = system
    clock = _TestClock()
    service = MockGateway(
        config=config, key_ring=ring, ledger=ledger or default_ledger, clock=clock
    )
    return RunBoundGateway(service, clock)


def test_cart_canonicalization_is_deterministic_and_order_independent() -> None:
    line_a = CartLine("p-a", 1, 100, "a")
    line_b = CartLine("p-b", 2, 200, None)
    first = Cart("merchant", 500, "INR", (line_b, line_a))
    second = Cart("merchant", 500, "INR", (line_a, line_b))
    assert canonical_cart_bytes(first) == canonical_cart_bytes(second)
    assert cart_hash(first) == cart_hash(second)
    assert len(cart_hash(first)) == 64


def test_cart_hash_changes_for_every_purchase_relevant_field() -> None:
    original = make_cart()
    variants = (
        make_cart(merchant="fictional-merchant-b"),
        make_cart(product="fictional-ssd-2tb"),
        make_cart(tax=501),
        make_cart(currency="USD"),
    )
    assert all(cart_hash(candidate) != cart_hash(original) for candidate in variants)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"amount_minor": 1.5},
        {"amount_minor": True},
        {"currency": "inr"},
        {"items": ()},
        {"amount_minor": 99},
    ],
)
def test_invalid_cart_is_rejected(kwargs: dict[str, object]) -> None:
    base: dict[str, object] = {
        "merchant_id": "merchant",
        "amount_minor": 100,
        "currency": "INR",
        "items": (CartLine("p", 1, 100),),
    }
    base.update(kwargs)
    with pytest.raises((ValueError, TypeError)):
        Cart(**base)  # type: ignore[arg-type]


def test_cart_rejects_mutable_item_collection() -> None:
    with pytest.raises(ValueError):
        Cart("merchant", 100, "INR", [CartLine("p", 1, 100)])  # type: ignore[arg-type]


@pytest.mark.parametrize("persisted_result", ["BLOCK", "STEP_UP"])
def test_ledger_requires_persisted_allow(system, persisted_result: str) -> None:
    cart = make_cart()
    decision, credential = credential_fixture(system, cart)
    with sqlite3.connect(system[0]) as connection:
        connection.execute(
            "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "decision-1",
                "run-1",
                persisted_result,
                '["not_allowed"]',
                "policy-test-1",
                cart.amount_minor,
                cart.currency,
            ),
        )
    with pytest.raises(ValueError, match="no ALLOW decision"):
        system[1].create_after_allow(decision=decision, credential=credential)


def test_ledger_requires_persisted_decision(system) -> None:
    cart = make_cart()
    decision, credential = credential_fixture(system, cart)

    with pytest.raises(ValueError, match="no ALLOW decision"):
        system[1].create_after_allow(decision=decision, credential=credential)


def test_public_issuance_fails_closed_without_winner_cart_binding(system) -> None:
    cart = make_cart()
    with sqlite3.connect(system[0]) as connection:
        connection.execute(
            "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "decision-1",
                "run-1",
                "ALLOW",
                '["CHECKS_PASSED"]',
                "policy-test-1",
                cart.amount_minor,
                cart.currency,
            ),
        )

    with pytest.raises(CredentialIssuanceDenied, match="selected-product-to-cart binding"):
        issue_credential(
            decision=allow_decision(cart),
            cart=cart,
            signing_key=system[2],
            config=CONFIG,
            ledger=system[1],
            now=NOW,
        )
    with sqlite3.connect(system[0]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM credentials").fetchone()[0] == 0


@pytest.mark.parametrize("status", ["error", "timeout"])
def test_ledger_rejects_failed_or_timed_out_run(system, status: str) -> None:
    cart = make_cart()
    with sqlite3.connect(system[0]) as connection:
        connection.execute("UPDATE runs SET status = ? WHERE id = 'run-1'", (status,))
        connection.execute(
            "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "decision-1",
                "run-1",
                "ALLOW",
                '["CHECKS_PASSED"]',
                "policy-test-1",
                cart.amount_minor,
                cart.currency,
            ),
        )

    with pytest.raises(ValueError, match="non-failed run"):
        issue(system, cart)
    with sqlite3.connect(system[0]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM credentials").fetchone()[0] == 0


def test_test_fixture_credential_is_verified_and_redeemed_once(system) -> None:
    cart = make_cart()
    credential = issue(system, cart)
    result = gateway(system).authorize(
        token=credential.token, cart=cart, now=NOW + timedelta(seconds=1)
    )
    assert result.accepted is True
    assert result.code is RejectionCode.ACCEPTED
    replay = gateway(system).authorize(
        token=credential.token, cart=cart, now=NOW + timedelta(seconds=2)
    )
    assert replay.accepted is False
    assert replay.code is RejectionCode.CREDENTIAL_REPLAYED


def test_gateway_rejects_credential_from_another_run(system) -> None:
    credential = issue(system)
    result = MockGateway(
        config=CONFIG,
        key_ring=system[3],
        ledger=system[1],
        clock=lambda: NOW + timedelta(seconds=1),
    ).authorize(
        token=credential.token,
        cart=make_cart(),
        run_id="run-2",
    )
    assert result.accepted is False
    assert result.code is RejectionCode.RUN_MISMATCH


def test_ledger_accepts_an_injected_database_owner_engine(system) -> None:
    engine = create_engine(
        URL.create("sqlite", database=str(system[0])),
        connect_args={"check_same_thread": False},
    )
    clock = _TestClock(NOW + timedelta(seconds=1))
    ledger = SQLiteCredentialLedger(engine)
    cart = make_cart()
    credential = issue(system, cart, ledger=ledger)
    result = MockGateway(config=CONFIG, key_ring=system[3], ledger=ledger, clock=clock).authorize(
        token=credential.token, cart=cart, run_id="run-1"
    )
    assert result.accepted
    ledger.close()  # Injected engine remains owned by its application/database owner.
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1
    engine.dispose()


def test_missing_credential_is_rejected(system) -> None:
    result = gateway(system).authorize(token=None, cart=make_cart(), now=NOW)
    assert result.code is RejectionCode.MISSING_CREDENTIAL


def test_modified_token_fails_signature_validation(system) -> None:
    credential = issue(system)
    header, payload, signature = credential.token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=="))
    claims["amount_minor"] += 1
    replacement = (
        base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":")).encode())
        .rstrip(b"=")
        .decode()
    )
    result = gateway(system).authorize(
        token=f"{header}.{replacement}.{signature}",
        cart=make_cart(),
        now=NOW + timedelta(seconds=1),
    )
    assert result.accepted is False
    assert result.code is RejectionCode.SIGNATURE_INVALID


@pytest.mark.parametrize(
    ("cart", "expected"),
    [
        (make_cart(merchant="another-merchant"), RejectionCode.MERCHANT_MISMATCH),
        (make_cart(tax=501), RejectionCode.AMOUNT_MISMATCH),
        (make_cart(currency="USD"), RejectionCode.CURRENCY_MISMATCH),
        (make_cart(product="another-product"), RejectionCode.CART_MISMATCH),
    ],
)
def test_cart_merchant_amount_currency_mismatches_rejected(
    system, cart: Cart, expected: RejectionCode
) -> None:
    authorized = make_cart()
    credential = issue(system, authorized)
    result = gateway(system).authorize(
        token=credential.token, cart=cart, now=NOW + timedelta(seconds=1)
    )
    assert not result.accepted
    assert result.code is expected


def test_mismatch_does_not_redeem_nonce(system) -> None:
    authorized = make_cart()
    credential = issue(system, authorized)
    service = gateway(system)
    mismatched_carts = (
        make_cart(product="different-product"),
        Cart(
            authorized.merchant_id,
            authorized.amount_minor,
            authorized.currency,
            (CartLine("fictional-ssd-1tb", 2, 10_000, "OTHER-SKU"),),
            tax_minor=500,
        ),
        Cart(
            authorized.merchant_id,
            authorized.amount_minor,
            authorized.currency,
            (CartLine("fictional-ssd-1tb", 1, 10_000, "SSD-1T-A"),),
            tax_minor=10_500,
        ),
        Cart(
            authorized.merchant_id,
            authorized.amount_minor,
            authorized.currency,
            (CartLine("fictional-ssd-1tb", 2, 10_001, "SSD-1T-A"),),
            tax_minor=498,
        ),
        Cart(
            authorized.merchant_id,
            authorized.amount_minor,
            authorized.currency,
            authorized.items,
            tax_minor=499,
            shipping_minor=1,
        ),
        Cart(
            authorized.merchant_id,
            authorized.amount_minor,
            authorized.currency,
            authorized.items,
            tax_minor=501,
            discount_minor=1,
        ),
        Cart(
            authorized.merchant_id,
            authorized.amount_minor,
            authorized.currency,
            (authorized.items[0], CartLine("extra-item", 1, 0, "EXTRA")),
            tax_minor=500,
        ),
    )
    for mismatched_cart in mismatched_carts:
        mismatched = service.authorize(
            token=credential.token,
            cart=mismatched_cart,
            now=NOW + timedelta(seconds=1),
        )
        assert mismatched.code is RejectionCode.CART_MISMATCH
    accepted = service.authorize(
        token=credential.token, cart=authorized, now=NOW + timedelta(seconds=2)
    )
    assert accepted.accepted


def test_credential_is_rejected_if_allow_decision_is_revoked(system) -> None:
    credential = issue(system)
    with sqlite3.connect(system[0]) as connection:
        connection.execute("UPDATE decisions SET result = 'BLOCK' WHERE run_id = 'run-1'")
    result = gateway(system).authorize(
        token=credential.token, cart=make_cart(), now=NOW + timedelta(seconds=1)
    )
    assert result.code is RejectionCode.CREDENTIAL_REVOKED


def test_expired_credential_rejected(system) -> None:
    config = CredentialConfig("warrant-test", ttl_seconds=60)
    credential = issue(system, config=config)
    result = gateway(system, config=config).authorize(
        token=credential.token, cart=make_cart(), now=NOW + timedelta(seconds=60)
    )
    assert result.code is RejectionCode.CREDENTIAL_EXPIRED


@pytest.mark.parametrize(
    ("claim_change", "expected"),
    [
        ({"iss": "other-issuer"}, RejectionCode.MALFORMED_CREDENTIAL),
        ({"aud": "other-audience"}, RejectionCode.MALFORMED_CREDENTIAL),
        ({"amount_minor": True}, RejectionCode.MALFORMED_CREDENTIAL),
        ({"currency": "inr"}, RejectionCode.MALFORMED_CREDENTIAL),
        ({"v": 2}, RejectionCode.MALFORMED_CREDENTIAL),
        ({"iat": int(NOW.timestamp()) + 10}, RejectionCode.MALFORMED_CREDENTIAL),
        ({"exp": int(NOW.timestamp())}, RejectionCode.CREDENTIAL_EXPIRED),
        ({"approval_hash": "b" * 64}, RejectionCode.CREDENTIAL_NOT_ISSUED),
    ],
)
def test_signed_jwt_claim_validation_matrix(system, claim_change, expected) -> None:
    cart = make_cart()
    claims = {
        "amount_minor": cart.amount_minor,
        "approval_hash": APPROVAL_HASH,
        "aud": CONFIG.audience,
        "cart_hash": cart_hash(cart),
        "currency": cart.currency,
        "exp": int(NOW.timestamp()) + 60,
        "iat": int(NOW.timestamp()),
        "iss": CONFIG.issuer,
        "jti": "not-persisted",
        "merchant_id": cart.merchant_id,
        "run_id": "run-1",
        "v": 1,
    }
    claims.update(claim_change)
    token = jwt.encode(
        claims,
        system[2].private_key,
        algorithm="EdDSA",
        headers={"kid": system[2].key_id, "typ": "JWT"},
    )

    result = gateway(system).authorize(token=token, cart=cart, now=NOW + timedelta(seconds=1))

    assert result.accepted is False
    assert result.code is expected


@pytest.mark.parametrize(
    "missing_claim",
    [
        "approval_hash",
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
)
def test_missing_required_jwt_claim_is_rejected(system, missing_claim: str) -> None:
    cart = make_cart()
    claims = {
        "amount_minor": cart.amount_minor,
        "approval_hash": APPROVAL_HASH,
        "aud": CONFIG.audience,
        "cart_hash": cart_hash(cart),
        "currency": cart.currency,
        "exp": int(NOW.timestamp()) + 60,
        "iat": int(NOW.timestamp()),
        "iss": CONFIG.issuer,
        "jti": "not-persisted",
        "merchant_id": cart.merchant_id,
        "run_id": "run-1",
        "v": 1,
    }
    del claims[missing_claim]
    token = jwt.encode(
        claims,
        system[2].private_key,
        algorithm="EdDSA",
        headers={"kid": system[2].key_id, "typ": "JWT"},
    )

    result = gateway(system).authorize(token=token, cart=cart, now=NOW + timedelta(seconds=1))

    assert result.accepted is False
    assert result.code is RejectionCode.MALFORMED_CREDENTIAL


def test_gateway_rejects_disallowed_jwt_algorithm(system) -> None:
    cart = make_cart()
    token = jwt.encode(
        {"iss": CONFIG.issuer, "aud": CONFIG.audience},
        "test-only-not-a-warrant-key-at-least-32-bytes-long",
        algorithm="HS256",
        headers={"kid": system[2].key_id, "typ": "JWT"},
    )

    result = gateway(system).authorize(token=token, cart=cart, now=NOW)

    assert result.accepted is False
    assert result.code is RejectionCode.MALFORMED_CREDENTIAL


def test_gateway_rejects_unexpected_jwt_header_fields(system) -> None:
    cart = make_cart()
    token = jwt.encode(
        {"iss": CONFIG.issuer, "aud": CONFIG.audience},
        system[2].private_key,
        algorithm="EdDSA",
        headers={"kid": system[2].key_id, "typ": "JWT", "x-unexpected": "value"},
    )

    result = gateway(system).authorize(token=token, cart=cart, now=NOW)

    assert result.accepted is False
    assert result.code is RejectionCode.MALFORMED_CREDENTIAL


def test_zero_amount_cart_is_characterized_as_valid_mock_authorization(system) -> None:
    cart = Cart(
        merchant_id="fictional-free-merchant",
        amount_minor=0,
        currency="INR",
        items=(CartLine("fictional-free-item", 1, 0),),
    )
    credential = issue(system, cart)

    result = gateway(system).authorize(
        token=credential.token, cart=cart, now=NOW + timedelta(seconds=1)
    )

    assert result.accepted is True
    assert result.code is RejectionCode.ACCEPTED


def test_unknown_key_and_malformed_token_rejected(system) -> None:
    credential = issue(system)
    unknown_ring = KeyRing(())
    result = MockGateway(
        config=CONFIG, key_ring=unknown_ring, ledger=system[1], clock=lambda: NOW
    ).authorize(token=credential.token, cart=make_cart(), run_id="run-1")
    assert result.code is RejectionCode.UNKNOWN_KEY
    malformed = gateway(system).authorize(token="not-a-jwt", cart=make_cart(), now=NOW)
    assert malformed.code is RejectionCode.MALFORMED_CREDENTIAL


def test_concurrent_redemption_accepts_exactly_one_request(system) -> None:
    cart = make_cart()
    credential = issue(system, cart)
    service = gateway(system)
    attempt_count = 12
    start = Barrier(attempt_count)

    def redeem_once() -> object:
        start.wait(timeout=10)
        return service.authorize(token=credential.token, cart=cart, now=NOW + timedelta(seconds=1))

    with ThreadPoolExecutor(max_workers=attempt_count) as executor:
        results = list(executor.map(lambda _: redeem_once(), range(attempt_count)))
    assert sum(result.accepted for result in results) == 1
    assert sum(result.code is RejectionCode.CREDENTIAL_REPLAYED for result in results) == 11


def test_direct_ledger_missing_tables_and_signing_key_fail_closed(system, tmp_path) -> None:
    cart = make_cart()
    decision, credential = credential_fixture(system, cart)
    with pytest.raises(SQLAlchemyError):
        SQLiteCredentialLedger(tmp_path / "missing-tables.sqlite3").create_after_allow(
            decision=decision,
            credential=credential,
        )

    missing = tmp_path / "not-created.pem"
    from warrant.credential.keys import load_signing_key

    with pytest.raises(KeyConfigurationError):
        load_signing_key(missing, "passphrase", "key-1")


def test_gateway_database_failure_rejects(system, tmp_path) -> None:
    credential = issue(system)
    broken = SQLiteCredentialLedger(tmp_path / "no-schema.sqlite3")
    result = gateway(system, ledger=broken).authorize(
        token=credential.token, cart=make_cart(), now=NOW + timedelta(seconds=1)
    )
    assert result.accepted is False
    assert result.code is RejectionCode.DATABASE_ERROR


def test_gateway_unexpected_ledger_error_is_sanitized_and_fails_closed(system) -> None:
    class BrokenLedger:
        def redeem_once(self, **kwargs):
            raise RuntimeError("private driver connection string")

    credential = issue(system)
    result = gateway(system, ledger=BrokenLedger()).authorize(
        token=credential.token, cart=make_cart(), now=NOW + timedelta(seconds=1)
    )

    assert result.accepted is False
    assert result.code is RejectionCode.DATABASE_ERROR


def test_failed_redemption_rolls_back_and_nonce_can_be_retried(system) -> None:
    cart = make_cart()
    credential = issue(system, cart)
    with sqlite3.connect(system[0]) as connection:
        connection.execute(
            """CREATE TRIGGER reject_redemption
               BEFORE UPDATE OF redeemed_at ON credentials
               BEGIN SELECT RAISE(ABORT, 'private redemption failure'); END"""
        )

    rejected = gateway(system).authorize(
        token=credential.token, cart=cart, now=NOW + timedelta(seconds=1)
    )
    assert rejected.accepted is False
    assert rejected.code is RejectionCode.DATABASE_ERROR
    with sqlite3.connect(system[0]) as connection:
        redeemed_at = connection.execute(
            "SELECT redeemed_at FROM credentials WHERE nonce = ?", (credential.nonce,)
        ).fetchone()[0]
        connection.execute("DROP TRIGGER reject_redemption")
    assert redeemed_at is None

    retried = gateway(system).authorize(
        token=credential.token, cart=cart, now=NOW + timedelta(seconds=2)
    )
    assert retried.accepted is True


def test_public_issuer_guard_rejects_before_calling_ledger(system) -> None:
    cart = make_cart()

    class BrokenLedger:
        called = False

        def create_after_allow(self, *, decision, credential):
            self.called = True

    ledger = BrokenLedger()
    with pytest.raises(CredentialIssuanceDenied) as error:
        issue_credential(
            decision=allow_decision(cart),
            cart=cart,
            signing_key=system[2],
            config=CONFIG,
            ledger=ledger,
            now=NOW,
        )
    assert "verified selected-product-to-cart binding" in str(error.value)
    assert ledger.called is False


def test_persisted_allow_amount_must_match_credential(system) -> None:
    cart = make_cart()
    decision, credential = credential_fixture(system, cart)
    with sqlite3.connect(system[0]) as connection:
        connection.execute(
            "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("decision-1", "run-1", "ALLOW", '["CHECKS_PASSED"]', "policy-test-1", 1, "INR"),
        )
    with pytest.raises(ValueError, match="persisted decision does not match"):
        system[1].create_after_allow(decision=decision, credential=credential)


def test_persisted_allow_currency_must_match_credential(system) -> None:
    cart = make_cart()
    decision, credential = credential_fixture(system, cart)
    with sqlite3.connect(system[0]) as connection:
        connection.execute(
            "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "decision-1",
                "run-1",
                "ALLOW",
                '["CHECKS_PASSED"]',
                "policy-test-1",
                cart.amount_minor,
                "USD",
            ),
        )
    with pytest.raises(ValueError, match="persisted decision does not match"):
        system[1].create_after_allow(decision=decision, credential=credential)


@pytest.mark.parametrize(
    ("policy_version", "reasons"),
    [("different-policy", '["CHECKS_PASSED"]'), ("policy-test-1", '["other-reason"]')],
)
def test_persisted_allow_must_match_decision_version_and_reasons(
    system, policy_version: str, reasons: str
) -> None:
    cart = make_cart()
    with sqlite3.connect(system[0]) as connection:
        connection.execute(
            "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "decision-1",
                "run-1",
                "ALLOW",
                reasons,
                policy_version,
                cart.amount_minor,
                cart.currency,
            ),
        )

    decision, credential = credential_fixture(system, cart)
    with pytest.raises(ValueError, match="persisted decision does not match"):
        system[1].create_after_allow(decision=decision, credential=credential)


def test_encrypted_key_generation_loading_and_no_overwrite(tmp_path) -> None:
    private_path = tmp_path / "keys" / "private.pem"
    public_path = tmp_path / "keys" / "public.pem"
    generate_key_pair(private_path, public_path, "a long local test passphrase")
    loaded_private = load_signing_key(private_path, "a long local test passphrase", "rot-1")
    loaded_public = load_verification_key(public_path, "rot-1")
    assert (
        loaded_private.private_key.public_key().public_bytes_raw()
        == loaded_public.public_key.public_bytes_raw()
    )
    with pytest.raises(KeyConfigurationError):
        generate_key_pair(private_path, public_path, "another passphrase")


def test_key_generation_does_not_leave_a_private_file_if_public_output_exists(tmp_path) -> None:
    private_path = tmp_path / "private.pem"
    public_path = tmp_path / "public.pem"
    public_path.write_text("existing public file", encoding="utf-8")
    with pytest.raises(KeyConfigurationError):
        generate_key_pair(private_path, public_path, "a sufficiently long passphrase")
    assert not private_path.exists()
    assert public_path.read_text(encoding="utf-8") == "existing public file"
