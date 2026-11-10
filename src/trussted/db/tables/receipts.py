"""Public signing keys and immutable finalized audit receipts."""

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from trussted.db.base import Base


class SigningKeyRow(Base):
    """Historical public verification keys survive revocation."""

    __tablename__ = "signing_keys"
    __table_args__ = (CheckConstraint("algorithm = 'ed25519'", name="algorithm"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    algorithm: Mapped[str] = mapped_column(Text)
    public_key: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text)
    revoked_at: Mapped[str | None] = mapped_column(Text)


class ReceiptRow(Base):
    """One final signed audit receipt per run."""

    __tablename__ = "receipts"
    __table_args__ = (UniqueConstraint("run_id"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="RESTRICT"))
    final_hash: Mapped[str] = mapped_column(Text)
    signature: Mapped[str] = mapped_column(Text)
    signing_key_id: Mapped[str] = mapped_column(ForeignKey("signing_keys.id", ondelete="RESTRICT"))
    created_at: Mapped[str] = mapped_column(Text)
    export_path: Mapped[str] = mapped_column(Text)


class ReceiptEventRow(Base):
    """Ordered append-only event records belonging to a finalized receipt."""

    __tablename__ = "receipt_events"
    __table_args__ = (
        UniqueConstraint("receipt_id", "seq"),
        CheckConstraint("seq >= 0", name="sequence"),
        CheckConstraint(
            "type IN ('intent','observation','facts','conflicts','ranking','stability',"
            "'decision','credential','settlement')",
            name="event_type",
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    receipt_id: Mapped[str] = mapped_column(ForeignKey("receipts.id", ondelete="RESTRICT"))
    seq: Mapped[int]
    type: Mapped[str] = mapped_column(Text)
    payload: Mapped[str] = mapped_column(Text)
    payload_hash: Mapped[str] = mapped_column(Text)
    prev_hash: Mapped[str] = mapped_column(Text)
    event_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text)
