"""Store public keys and immutable finalized receipt evidence."""

import sqlalchemy as sa
from alembic import op

revision = "0005_receipts"
down_revision = "0004_outcomes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add restrictive receipt relationships and SQLite mutation-blocking triggers."""
    op.create_table(
        "signing_keys",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("algorithm", sa.Text(), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("revoked_at", sa.Text()),
        sa.CheckConstraint("algorithm = 'ed25519'", name="algorithm"),
    )
    op.create_table(
        "receipts",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "run_id", sa.Text(), sa.ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("final_hash", sa.Text(), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column(
            "signing_key_id",
            sa.Text(),
            sa.ForeignKey("signing_keys.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("export_path", sa.Text(), nullable=False),
        sa.UniqueConstraint("run_id"),
    )
    op.create_table(
        "receipt_events",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "receipt_id",
            sa.Text(),
            sa.ForeignKey("receipts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("payload_hash", sa.Text(), nullable=False),
        sa.Column("prev_hash", sa.Text(), nullable=False),
        sa.Column("event_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("receipt_id", "seq"),
        sa.CheckConstraint("seq >= 0", name="sequence"),
        sa.CheckConstraint(
            "type IN ('intent','observation','facts','conflicts','ranking','stability',"
            "'decision','credential','settlement')",
            name="event_type",
        ),
    )
    if op.get_bind().dialect.name == "sqlite":
        for table in ("receipts", "receipt_events"):
            for operation in ("UPDATE", "DELETE"):
                op.execute(
                    sa.text(
                        f"CREATE TRIGGER {table}_no_{operation.lower()} "
                        f"BEFORE {operation} ON {table} "
                        "BEGIN SELECT RAISE(ABORT, 'finalized receipt evidence is immutable'); END"
                    )
                )


def downgrade() -> None:
    """Drop audit storage only during an explicitly requested schema rollback."""
    if op.get_bind().dialect.name == "sqlite":
        for table in ("receipt_events", "receipts"):
            for operation in ("update", "delete"):
                op.execute(sa.text(f"DROP TRIGGER {table}_no_{operation}"))
    op.drop_table("receipt_events")
    op.drop_table("receipts")
    op.drop_table("signing_keys")
