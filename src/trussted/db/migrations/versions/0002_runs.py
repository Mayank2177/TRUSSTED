"""Create run lifecycle and provenance storage."""

import sqlalchemy as sa
from alembic import op

revision = "0002_runs"
down_revision = "0001_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add reproducible run records with nullable unfinished measurements."""
    op.create_table(
        "runs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("batch_id", sa.Text(), sa.ForeignKey("benchmark_batches.id"), nullable=False),
        sa.Column("scenario_id", sa.Text(), sa.ForeignKey("scenarios.id"), nullable=False),
        sa.Column("variant_id", sa.Text(), sa.ForeignKey("agent_variants.id"), nullable=False),
        sa.Column("repetition", sa.Integer(), nullable=False),
        sa.Column("seed", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("intent", sa.Text(), nullable=False),
        sa.Column("input_manifest", sa.Text(), nullable=False),
        sa.Column("stage_states", sa.Text(), nullable=False),
        sa.Column("purchased_item", sa.Text()),
        sa.Column(
            "attacker_success", sa.Boolean(name="attacker_success_bool", create_constraint=True)
        ),
        sa.Column("benign_success", sa.Boolean(name="benign_success_bool", create_constraint=True)),
        sa.Column("false_block", sa.Boolean(name="false_block_bool", create_constraint=True)),
        sa.Column("latency_ms", sa.BigInteger()),
        sa.Column("llm_cost_micro_usd", sa.BigInteger()),
        sa.Column("started_at", sa.Text(), nullable=False),
        sa.Column("finished_at", sa.Text()),
        sa.Column("error_stage", sa.Text()),
        sa.Column("error_code", sa.Text()),
        sa.UniqueConstraint("batch_id", "scenario_id", "variant_id", "repetition"),
        sa.CheckConstraint("repetition >= 1", name="positive_repetition"),
        sa.CheckConstraint("status IN ('running','completed','error','timeout')", name="status"),
        sa.CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="latency"),
        sa.CheckConstraint("llm_cost_micro_usd IS NULL OR llm_cost_micro_usd >= 0", name="cost"),
    )
    op.create_index(
        "ix_runs_batch_scenario_variant", "runs", ["batch_id", "scenario_id", "variant_id"]
    )


def downgrade() -> None:
    """Remove run storage only during an explicitly requested migration rollback."""
    op.drop_table("runs")
