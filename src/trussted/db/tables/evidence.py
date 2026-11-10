"""Evidence rows with same-run observation and winner foreign keys."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from trussted.db.base import Base


class ObservationRow(Base):
    """Content metadata belonging to one run."""

    __tablename__ = "observations"
    __table_args__ = (
        UniqueConstraint("id", "run_id"),
        CheckConstraint("byte_size >= 0", name="nonnegative_byte_size"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    url: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(Text)
    byte_size: Mapped[int] = mapped_column(BigInteger)
    fetched_at: Mapped[str] = mapped_column(Text)


class ProductFactRow(Base):
    """An extraction whose observation must belong to its own run."""

    __tablename__ = "product_facts"
    __table_args__ = (
        UniqueConstraint("id", "run_id"),
        ForeignKeyConstraint(
            ["observation_id", "run_id"], ["observations.id", "observations.run_id"]
        ),
        CheckConstraint("price_minor >= 0", name="nonnegative_price"),
        Index("ix_product_facts_run_id", "run_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    observation_id: Mapped[str] = mapped_column(Text)
    sku: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    price_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(Text)
    spec: Mapped[str] = mapped_column(Text)
    gtin: Mapped[str | None] = mapped_column(Text)
    seller_id: Mapped[str] = mapped_column(Text)
    source_span: Mapped[str] = mapped_column(Text)


class FactConflictRow(Base):
    """A reference discrepancy for a persisted product fact."""

    __tablename__ = "fact_conflicts"
    __table_args__ = (
        CheckConstraint("severity IN ('low','medium','high')", name="severity"),
        Index("ix_fact_conflicts_fact_id", "fact_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    fact_id: Mapped[str] = mapped_column(ForeignKey("product_facts.id"))
    field: Mapped[str] = mapped_column(Text)
    extracted_value: Mapped[str] = mapped_column(Text)
    reference_value: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(Text)
    reference_source: Mapped[str] = mapped_column(Text)


class RankingRow(Base):
    """Ordered JSON candidates, plus a relationally constrained optional winner."""

    __tablename__ = "rankings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["winner_fact_id", "run_id"], ["product_facts.id", "product_facts.run_id"]
        ),
        Index("ix_rankings_run_id_perturbation", "run_id", "perturbation"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    perturbation: Mapped[str] = mapped_column(Text)
    ordered_fact_ids: Mapped[str] = mapped_column(Text)
    scores: Mapped[str] = mapped_column(Text)
    winner_fact_id: Mapped[str | None] = mapped_column(Text)
