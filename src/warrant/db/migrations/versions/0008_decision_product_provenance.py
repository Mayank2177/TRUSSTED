"""Backfill provable ALLOW winners and persist decision provenance.

Before changing the schema, require exactly one base-ranking row with a non-NULL winner
for each historical ALLOW decision. If any winner is missing or ambiguous, abort and
report the affected decision/run IDs. Backfill only that uniquely recorded winner; do
not fabricate historical approval hashes. Legacy non-ALLOW decisions may retain NULL
winner provenance.
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_decision_product_provenance"
down_revision = "0007_immutable_insert_guards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Backfill only uniquely provable winners and preserve other history untouched."""
    bind = op.get_bind()
    unresolved = bind.execute(
        sa.text(
            "SELECT d.id, d.run_id FROM decisions AS d LEFT JOIN rankings AS r "
            "ON r.run_id=d.run_id AND r.perturbation='none' "
            "WHERE d.result='ALLOW' GROUP BY d.id, d.run_id "
            "HAVING COUNT(r.winner_fact_id) != 1 ORDER BY d.run_id"
        )
    ).all()
    if unresolved:
        detail = ", ".join(f"{row.id} (run {row.run_id})" for row in unresolved)
        raise RuntimeError(
            "Cannot add mandatory winner provenance: these historical ALLOW decisions do not "
            "have exactly one base ranking winner: "
            f"{detail}. Reconcile the authoritative ranking history; no records were changed."
        )
    with op.batch_alter_table("decisions") as batch:
        batch.add_column(sa.Column("winner_fact_id", sa.Text(), nullable=True))
        batch.add_column(sa.Column("approval_hash", sa.Text(), nullable=True))
        batch.create_foreign_key(
            "fk_decisions_winner_fact_same_run",
            "product_facts",
            ["winner_fact_id", "run_id"],
            ["id", "run_id"],
        )
    bind.execute(
        sa.text(
            "UPDATE decisions SET winner_fact_id=(SELECT r.winner_fact_id FROM rankings AS r "
            "WHERE r.run_id=decisions.run_id AND r.perturbation='none') "
            "WHERE result='ALLOW'"
        )
    )
    with op.batch_alter_table("decisions") as batch:
        batch.create_check_constraint(
            "ck_decisions_allow_winner_required",
            "result != 'ALLOW' OR winner_fact_id IS NOT NULL",
        )
    with op.batch_alter_table("credentials") as batch:
        batch.add_column(sa.Column("approval_hash", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove only fields introduced by this revision."""
    with op.batch_alter_table("credentials") as batch:
        batch.drop_column("approval_hash")
    with op.batch_alter_table("decisions") as batch:
        batch.drop_constraint("ck_decisions_allow_winner_required", type_="check")
        batch.drop_constraint("fk_decisions_winner_fact_same_run", type_="foreignkey")
        batch.drop_column("approval_hash")
        batch.drop_column("winner_fact_id")
