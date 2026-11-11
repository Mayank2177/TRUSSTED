"""SQLite adapter for the credentials/decisions tables defined by DATABASE.md.

This module issues no DDL and owns no migration. It uses only the agreed table/column contract.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, Connection

from warrant.credential.token import (
    CredentialAlreadyIssued,
    CredentialLedger,
    IssuedCredential,
)
from warrant.policy.models import Decision, DecisionResult


class RedemptionStatus(StrEnum):
    REDEEMED = "REDEEMED"
    NOT_FOUND = "NOT_FOUND"
    REPLAYED = "REPLAYED"
    MISMATCH = "MISMATCH"
    DECISION_REVOKED = "DECISION_REVOKED"
    EXPIRED = "EXPIRED"


class SQLiteCredentialLedger(CredentialLedger):
    def __init__(self, database: Path | str | Engine, *, busy_timeout_ms: int = 5000) -> None:
        if type(busy_timeout_ms) is not int or busy_timeout_ms <= 0:
            raise ValueError("busy_timeout_ms must be positive")
        if isinstance(database, Engine):
            if database.dialect.name != "sqlite":
                raise ValueError("SQLiteCredentialLedger requires a SQLite SQLAlchemy engine")
            self._engine = database
            self._owns_engine = False
        else:
            self._engine = create_engine(
                URL.create("sqlite", database=str(Path(database).resolve())),
                connect_args={
                    "timeout": busy_timeout_ms / 1000,
                    "check_same_thread": False,
                },
            )
            self._owns_engine = True
        self._busy_timeout_ms = busy_timeout_ms

    def close(self) -> None:
        """Dispose an adapter-owned engine; an injected application engine stays owner-managed."""
        if self._owns_engine:
            self._engine.dispose()

    def _connect(self) -> Connection:
        connection = self._engine.connect()
        try:
            # Apply per-connection SQLite settings without taking ownership of schema/WAL setup.
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.exec_driver_sql(f"PRAGMA busy_timeout={self._busy_timeout_ms}")
            connection.commit()
            return connection
        except Exception:
            connection.close()
            raise

    def create_after_allow(self, *, decision: Decision, credential: IssuedCredential) -> None:
        connection = self._connect()
        try:
            # SQLite serializes writers from this point through commit. The existence check
            # and insert therefore cannot race with another issuer for the same run.
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            if credential.run_id != decision.run_id:
                raise ValueError("credential run ID does not match the ALLOW decision")
            if not decision.approval_hash or credential.approval_hash != decision.approval_hash:
                raise ValueError("credential approval hash does not match the ALLOW decision")
            existing = connection.execute(
                text("SELECT 1 FROM credentials WHERE run_id = :run_id LIMIT 1"),
                {"run_id": decision.run_id},
            ).first()
            if existing is not None:
                raise CredentialAlreadyIssued("a credential has already been issued for this run")
            run = (
                connection.execute(
                    text("SELECT status FROM runs WHERE id = :run_id"),
                    {"run_id": decision.run_id},
                )
                .mappings()
                .first()
            )
            if run is None or run["status"] not in {"running", "completed"}:
                raise ValueError("credential requires an existing non-failed run")
            row = (
                connection.execute(
                    text(
                        "SELECT result, amount_minor, currency, policy_version, reasons "
                        "FROM decisions WHERE run_id = :run_id"
                    ),
                    {"run_id": decision.run_id},
                )
                .mappings()
                .first()
            )
            if row is None or row["result"] != DecisionResult.ALLOW.value:
                raise ValueError("database has no ALLOW decision for this run")
            if decision.result is not DecisionResult.ALLOW:
                raise ValueError("credential insert requires ALLOW")
            try:
                persisted_reasons = json.loads(row["reasons"])
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValueError("persisted decision reasons are invalid") from exc
            expected_reasons = [reason.value for reason in decision.reasons]
            if (
                row["amount_minor"] != credential.amount_minor
                or row["currency"] != credential.currency
                or decision.amount_minor != credential.amount_minor
                or decision.currency != credential.currency
                or row["policy_version"] != decision.policy_version
                or persisted_reasons != expected_reasons
            ):
                raise ValueError("persisted decision does not match the supplied authorization")
            connection.execute(
                text("""INSERT INTO credentials
                   (id, run_id, cart_hash, merchant_id, amount_minor, currency, nonce,
                    expires_at, redeemed_at, signature, approval_hash)
                   VALUES (:id, :run_id, :cart_hash, :merchant_id, :amount_minor, :currency,
                           :nonce, :expires_at, NULL, :signature, :approval_hash)"""),
                {
                    "id": credential.credential_id,
                    "run_id": decision.run_id,
                    "cart_hash": credential.cart_hash,
                    "merchant_id": credential.merchant_id,
                    "amount_minor": credential.amount_minor,
                    "currency": credential.currency,
                    "nonce": credential.nonce,
                    "expires_at": _utc_text(credential.expires_at),
                    "signature": credential.signature,
                    "approval_hash": credential.approval_hash,
                },
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def redeem_once(
        self,
        *,
        nonce: str,
        run_id: str,
        signature: str,
        approval_hash: str | None = None,
        cart_hash: str,
        merchant_id: str,
        amount_minor: int,
        currency: str,
        now: datetime,
    ) -> RedemptionStatus:
        connection = self._connect()
        try:
            # Serializes competing SQLite writers before checking and setting redeemed_at.
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            row = (
                connection.execute(
                    text("""SELECT c.id, c.run_id, c.cart_hash, c.merchant_id, c.amount_minor,
                          c.currency, c.expires_at, c.redeemed_at, c.signature,
                          c.approval_hash, d.result
                   FROM credentials AS c
                   LEFT JOIN decisions AS d ON d.run_id = c.run_id
                   WHERE c.nonce = :nonce"""),
                    {"nonce": nonce},
                )
                .mappings()
                .first()
            )
            if row is None:
                connection.rollback()
                return RedemptionStatus.NOT_FOUND
            if row["run_id"] != run_id:
                connection.rollback()
                return RedemptionStatus.MISMATCH
            if row["redeemed_at"] is not None:
                connection.rollback()
                return RedemptionStatus.REPLAYED
            if row["result"] != DecisionResult.ALLOW.value:
                connection.rollback()
                return RedemptionStatus.DECISION_REVOKED
            if approval_hash is not None and row["approval_hash"] != approval_hash:
                connection.rollback()
                return RedemptionStatus.MISMATCH
            expected = (cart_hash, merchant_id, amount_minor, currency, signature)
            stored = (
                row["cart_hash"],
                row["merchant_id"],
                row["amount_minor"],
                row["currency"],
                row["signature"],
            )
            if stored != expected:
                connection.rollback()
                return RedemptionStatus.MISMATCH
            expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
            if now >= expires_at:
                connection.rollback()
                return RedemptionStatus.EXPIRED
            cursor = connection.execute(
                text("""UPDATE credentials SET redeemed_at = :redeemed_at
                        WHERE id = :id AND redeemed_at IS NULL"""),
                {"redeemed_at": _utc_text(now), "id": row["id"]},
            )
            if cursor.rowcount != 1:
                connection.rollback()
                return RedemptionStatus.REPLAYED
            connection.commit()
            return RedemptionStatus.REDEEMED
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("database timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
