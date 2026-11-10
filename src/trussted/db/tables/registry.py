"""Version-pinned registry rows; public boundaries use validated contracts."""

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from trussted.db.base import Base


class ScenarioRow(Base):
    __tablename__ = "scenarios"
    __table_args__ = (
        UniqueConstraint("scenario_key", "version", name="uq_scenarios_scenario_key_version"),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("kind IN ('attack', 'benign')", name="kind"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    scenario_key: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    attack_type: Mapped[str | None] = mapped_column(Text)
    definition: Mapped[str] = mapped_column(Text)
    expected_outcome: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer)


class FixtureRow(Base):
    __tablename__ = "fixtures"
    __table_args__ = (UniqueConstraint("scenario_id", "name", name="uq_fixtures_scenario_id_name"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    scenario_id: Mapped[str] = mapped_column(Text, ForeignKey("scenarios.id"))
    name: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(Text)
    path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text)


class VariantRow(Base):
    __tablename__ = "agent_variants"
    __table_args__ = (
        UniqueConstraint("name", "config_hash", name="uq_agent_variants_name_config_hash"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text)
    config: Mapped[str] = mapped_column(Text)
    config_hash: Mapped[str] = mapped_column(Text)


class BatchRow(Base):
    __tablename__ = "benchmark_batches"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    created_at: Mapped[str] = mapped_column(Text)
    git_commit: Mapped[str] = mapped_column(Text)
    seed: Mapped[int] = mapped_column(BigInteger)
    notes: Mapped[str | None] = mapped_column(Text)
