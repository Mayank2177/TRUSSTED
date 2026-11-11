"""Require a single issued credential per run without silently deleting history."""

import sqlalchemy as sa
from alembic import op

revision = "0009_one_credential_per_run"
down_revision = "0008_decision_product_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fail with explicit duplicate run IDs before adding the database constraint."""
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            "SELECT run_id, COUNT(*) AS credential_count FROM credentials "
            "GROUP BY run_id HAVING COUNT(*) > 1 ORDER BY run_id"
        )
    ).all()
    if duplicates:
        detail = ", ".join(f"{row.run_id} ({row.credential_count})" for row in duplicates)
        raise RuntimeError(
            "Cannot enforce one credential per run; duplicate credentials exist for: "
            f"{detail}. Reconcile records manually under the data-retention policy, then retry. "
            "No records were changed."
        )
    with op.batch_alter_table("credentials") as batch:
        batch.create_unique_constraint("uq_credentials_run_id", ["run_id"])


def downgrade() -> None:
    """Remove only the one-per-run constraint on an explicit downgrade."""
    with op.batch_alter_table("credentials") as batch:
        batch.drop_constraint("uq_credentials_run_id", type_="unique")
