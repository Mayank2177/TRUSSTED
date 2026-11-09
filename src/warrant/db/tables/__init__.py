"""Persistence row mappings; import modules here as migrations are added."""

from warrant.db.tables.registry import BatchRow, FixtureRow, ScenarioRow, VariantRow

__all__ = [
    "BatchRow",
    "FixtureRow",
    "ScenarioRow",
    "VariantRow",
]
