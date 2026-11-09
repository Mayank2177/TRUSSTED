"""Immutable scenario revisions and reproducible benchmark registry.

Revision ID: 0001_registry
Revises: None
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_registry"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("scenario_key", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("attack_type", sa.Text(), nullable=True),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("expected_outcome", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_scenarios"),
        sa.UniqueConstraint("scenario_key", "version", name="uq_scenarios_scenario_key_version"),
        sa.CheckConstraint("version >= 1", name="ck_scenarios_version_positive"),
        sa.CheckConstraint("kind IN ('attack', 'benign')", name="ck_scenarios_kind"),
    )
    op.create_table(
        "fixtures",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("scenario_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_fixtures"),
        sa.ForeignKeyConstraint(
            ["scenario_id"], ["scenarios.id"], name="fk_fixtures_scenario_id_scenarios"
        ),
        sa.UniqueConstraint("scenario_id", "name", name="uq_fixtures_scenario_id_name"),
    )
    op.create_table(
        "agent_variants",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("config", sa.Text(), nullable=False),
        sa.Column("config_hash", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_agent_variants"),
        sa.UniqueConstraint("name", "config_hash", name="uq_agent_variants_name_config_hash"),
    )
    op.create_table(
        "benchmark_batches",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("git_commit", sa.Text(), nullable=False),
        sa.Column("seed", sa.BigInteger(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_benchmark_batches"),
    )
    if op.get_bind().dialect.name == "sqlite":
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER scenarios_no_{action.lower()} BEFORE {action} ON scenarios "
                "BEGIN SELECT RAISE(ABORT, 'scenario revisions are immutable'); END"
            )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS scenarios_no_delete")
        op.execute("DROP TRIGGER IF EXISTS scenarios_no_update")
    op.drop_table("benchmark_batches")
    op.drop_table("agent_variants")
    op.drop_table("fixtures")
    op.drop_table("scenarios")
