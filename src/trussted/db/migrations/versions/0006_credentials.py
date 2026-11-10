"""Store simulated credentials with unique single-use nonces."""

import sqlalchemy as sa
from alembic import op

revision = "0006_credentials"
down_revision = "0005_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add portable credential fields and the unique nonce constraint."""
    op.create_table(
        "credentials",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "run_id", sa.Text(), sa.ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("cart_hash", sa.Text(), nullable=False),
        sa.Column("merchant_id", sa.Text(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("nonce", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Text(), nullable=False),
        sa.Column("redeemed_at", sa.Text()),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.UniqueConstraint("nonce"),
        sa.CheckConstraint("amount_minor >= 0", name="amount"),
    )


def downgrade() -> None:
    """Remove simulated credential storage during an explicit schema rollback."""
    op.drop_table("credentials")
