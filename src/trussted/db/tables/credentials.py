"""Simulated credentials with unique single-use nonces."""

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from trussted.db.base import Base


class CredentialRow(Base):
    """Validated issued-token metadata and its optional consumption timestamp."""

    __tablename__ = "credentials"
    __table_args__ = (
        UniqueConstraint("nonce"),
        CheckConstraint("amount_minor >= 0", name="amount"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="RESTRICT"))
    cart_hash: Mapped[str] = mapped_column(Text)
    merchant_id: Mapped[str] = mapped_column(Text)
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(Text)
    nonce: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[str] = mapped_column(Text)
    redeemed_at: Mapped[str | None] = mapped_column(Text)
    signature: Mapped[str] = mapped_column(Text)
