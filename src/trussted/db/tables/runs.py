"""Run identity, provenance, lifecycle and outcome storage."""

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from trussted.db.base import Base


class RunRow(Base):
    """One reproducible attempt for a scenario revision and agent configuration."""

    __tablename__ = "runs"
    __table_args__ = (
        UniqueConstraint("batch_id", "scenario_id", "variant_id", "repetition"),
        CheckConstraint("repetition >= 1", name="positive_repetition"),
        CheckConstraint("status IN ('running','completed','error','timeout')", name="status"),
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="latency"),
        CheckConstraint("llm_cost_micro_usd IS NULL OR llm_cost_micro_usd >= 0", name="cost"),
        Index("ix_runs_batch_scenario_variant", "batch_id", "scenario_id", "variant_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("benchmark_batches.id"))
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"))
    variant_id: Mapped[str] = mapped_column(ForeignKey("agent_variants.id"))
    repetition: Mapped[int]
    seed: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(Text)
    input_manifest: Mapped[str] = mapped_column(Text)
    stage_states: Mapped[str] = mapped_column(Text)
    purchased_item: Mapped[str | None] = mapped_column(Text)
    attacker_success: Mapped[bool | None]
    benign_success: Mapped[bool | None]
    false_block: Mapped[bool | None]
    latency_ms: Mapped[int | None] = mapped_column(BigInteger)
    llm_cost_micro_usd: Mapped[int | None] = mapped_column(BigInteger)
    started_at: Mapped[str] = mapped_column(Text)
    finished_at: Mapped[str | None] = mapped_column(Text)
    error_stage: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(Text)
