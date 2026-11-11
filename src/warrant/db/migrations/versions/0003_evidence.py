"""Create extraction, cross-check and ranking evidence with same-run foreign keys."""

import sqlalchemy as sa
from alembic import op

revision = "0003_evidence"
down_revision = "0002_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add evidence storage without embedding raw content in the database."""
    op.create_table(
        "observations",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("fetched_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("id", "run_id"),
        sa.CheckConstraint("byte_size >= 0", name="nonnegative_byte_size"),
    )
    _create_facts()
    _create_conflicts()
    op.create_table(
        "rankings",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("perturbation", sa.Text(), nullable=False),
        sa.Column("ordered_fact_ids", sa.Text(), nullable=False),
        sa.Column("scores", sa.Text(), nullable=False),
        sa.Column("winner_fact_id", sa.Text()),
        sa.ForeignKeyConstraint(
            ["winner_fact_id", "run_id"],
            ["product_facts.id", "product_facts.run_id"],
        ),
    )
    op.create_index("ix_rankings_run_id_perturbation", "rankings", ["run_id", "perturbation"])


def _create_facts() -> None:
    op.create_table(
        "product_facts",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("observation_id", sa.Text(), nullable=False),
        sa.Column("sku", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("price_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("spec", sa.Text(), nullable=False),
        sa.Column("gtin", sa.Text()),
        sa.Column("seller_id", sa.Text(), nullable=False),
        sa.Column("source_span", sa.Text(), nullable=False),
        sa.UniqueConstraint("id", "run_id"),
        sa.ForeignKeyConstraint(
            ["observation_id", "run_id"],
            ["observations.id", "observations.run_id"],
        ),
        sa.CheckConstraint("price_minor >= 0", name="nonnegative_price"),
    )
    op.create_index("ix_product_facts_run_id", "product_facts", ["run_id"])


def _create_conflicts() -> None:
    op.create_table(
        "fact_conflicts",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("fact_id", sa.Text(), sa.ForeignKey("product_facts.id"), nullable=False),
        sa.Column("field", sa.Text(), nullable=False),
        sa.Column("extracted_value", sa.Text(), nullable=False),
        sa.Column("reference_value", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("reference_source", sa.Text(), nullable=False),
        sa.CheckConstraint("severity IN ('low','medium','high')", name="severity"),
    )
    op.create_index("ix_fact_conflicts_fact_id", "fact_conflicts", ["fact_id"])


def downgrade() -> None:
    """Drop dependents before their provenance parents on explicit rollback."""
    op.drop_table("rankings")
    op.drop_table("fact_conflicts")
    op.drop_table("product_facts")
    op.drop_table("observations")
