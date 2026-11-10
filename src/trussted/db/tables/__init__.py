"""Persistence row mappings; import modules here as migrations are added."""

from trussted.db.tables.credentials import CredentialRow
from trussted.db.tables.evidence import FactConflictRow, ObservationRow, ProductFactRow, RankingRow
from trussted.db.tables.outcomes import DecisionRow, StabilityRow
from trussted.db.tables.receipts import ReceiptEventRow, ReceiptRow, SigningKeyRow
from trussted.db.tables.registry import BatchRow, FixtureRow, ScenarioRow, VariantRow
from trussted.db.tables.runs import RunRow

__all__ = [
    "BatchRow",
    "FixtureRow",
    "ScenarioRow",
    "VariantRow",
    "RunRow",
    "ObservationRow",
    "ProductFactRow",
    "FactConflictRow",
    "RankingRow",
    "StabilityRow",
    "DecisionRow",
    "SigningKeyRow",
    "ReceiptRow",
    "ReceiptEventRow",
    "CredentialRow",
]
