"""Final per-run stability and policy outcomes."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from warrant.db.base import Base


class StabilityRow(Base):
    """One final perturbation result per run, independent of skipped stage states."""

    __tablename__ = "stability_reports"
    __table_args__ = (
        UniqueConstraint("run_id"),
        CheckConstraint("threshold >= 0 AND threshold <= 1", name="threshold_range"),
        CheckConstraint("stable IN (0,1)", name="stable_boolean"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    winner_counts: Mapped[str] = mapped_column(Text)
    stable: Mapped[bool] = mapped_column(Boolean)
    threshold: Mapped[float] = mapped_column(Float)
    flips: Mapped[str] = mapped_column(Text)


class DecisionRow(Base):
    """An explicit policy decision; duplicate writes cannot replace prior decisions."""

    __tablename__ = "decisions"
    __table_args__ = (
        UniqueConstraint("run_id"),
        CheckConstraint("result IN ('ALLOW','STEP_UP','BLOCK')", name="result"),
        CheckConstraint("amount_minor >= 0", name="nonnegative_amount"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    result: Mapped[str] = mapped_column(Text)
    reasons: Mapped[str] = mapped_column(Text)
    policy_version: Mapped[str] = mapped_column(Text)
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(Text)
