"""Reject replacement collisions even on clients with recursive triggers disabled."""

import sqlalchemy as sa
from alembic import op

revision = "0007_immutable_insert_guards"
down_revision = "0006_credentials"
branch_labels = None
depends_on = None

_IDENTITIES = {
    "scenarios": "id=NEW.id OR (scenario_key=NEW.scenario_key AND version=NEW.version)",
    "receipts": "id=NEW.id OR run_id=NEW.run_id",
    "receipt_events": "id=NEW.id OR (receipt_id=NEW.receipt_id AND seq=NEW.seq)",
}


def upgrade() -> None:
    """Protect immutable identities before SQLite REPLACE can delete an old row."""
    if op.get_bind().dialect.name == "sqlite":
        for table, identity in _IDENTITIES.items():
            op.execute(
                sa.text(
                    f"CREATE TRIGGER {table}_no_replacement BEFORE INSERT ON {table} "
                    f"WHEN EXISTS (SELECT 1 FROM {table} WHERE {identity}) "
                    "BEGIN SELECT RAISE(ABORT, 'UNIQUE constraint failed: immutable identity'); END"
                )
            )


def downgrade() -> None:
    """Remove only this revision's insert guards on an explicit downgrade."""
    if op.get_bind().dialect.name == "sqlite":
        for table in _IDENTITIES:
            op.execute(sa.text(f"DROP TRIGGER {table}_no_replacement"))
