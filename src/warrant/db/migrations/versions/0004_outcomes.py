"""Create final stability reports and explicit policy decisions."""

import sqlalchemy as sa
from alembic import op

revision = "0004_outcomes"
down_revision = "0003_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add one final report and one decision per run."""
    op.create_table(
        "stability_reports",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("winner_counts", sa.Text(), nullable=False),
        sa.Column("stable", sa.Boolean(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("flips", sa.Text(), nullable=False),
        sa.UniqueConstraint("run_id"),
        sa.CheckConstraint("threshold >= 0 AND threshold <= 1", name="threshold_range"),
        sa.CheckConstraint("stable IN (0,1)", name="stable_boolean"),
    )
    op.create_table(
        "decisions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("reasons", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.UniqueConstraint("run_id"),
        sa.CheckConstraint("result IN ('ALLOW','STEP_UP','BLOCK')", name="result"),
        sa.CheckConstraint("amount_minor >= 0", name="nonnegative_amount"),
    )


def downgrade() -> None:
    """Remove outcome storage during an explicitly requested migration rollback."""
    op.drop_table("decisions")
    op.drop_table("stability_reports")
