"""Simulated credentials with unique single-use nonces."""

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from warrant.db.base import Base


class CredentialRow(Base):
    """Validated issued-token metadata and its optional consumption timestamp."""

    __tablename__ = "credentials"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="RESTRICT"))
    __table_args__ = (
        UniqueConstraint("nonce"),
        UniqueConstraint("run_id"),
        CheckConstraint("amount_minor >= 0", name="amount"),
    )
    cart_hash: Mapped[str] = mapped_column(Text)
    merchant_id: Mapped[str] = mapped_column(Text)
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(Text)
    nonce: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[str] = mapped_column(Text)
    redeemed_at: Mapped[str | None] = mapped_column(Text)
    signature: Mapped[str] = mapped_column(Text)
    approval_hash: Mapped[str | None] = mapped_column(Text)
