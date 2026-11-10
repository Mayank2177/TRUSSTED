"""Detached API/report results with explicit eligible and failed-run counts."""

from typing import Literal

from warrant.db.contracts import FrozenModel, Id, Money
from warrant.db.contracts.evidence import (
    FactConflictInput,
    ObservationInput,
    ProductFactInput,
    RankingInput,
)
from warrant.db.contracts.outcomes import DecisionInput, StabilityInput
from warrant.db.contracts.registry import ScenarioInput, VariantInput
from warrant.db.contracts.runs import RunRecord, RunStatus


class RunFilter(FrozenModel):
    """Supported run-list filters; scenario_id identifies an exact revision."""

    batch_id: Id | None = None
    scenario_id: Id | None = None
    variant_id: Id | None = None
    status: RunStatus | None = None


class RunPage(FrozenModel):
    """A stable, bounded page of detached run results."""

    items: tuple[RunRecord, ...]
    total: int
    limit: int
    offset: int


class RunDetail(FrozenModel):
    """Complete persisted pipeline evidence without an active ORM session."""

    run: RunRecord
    scenario: ScenarioInput
    variant: VariantInput
    observations: tuple[ObservationInput, ...]
    product_facts: tuple[ProductFactInput, ...]
    fact_conflicts: tuple[FactConflictInput, ...]
    rankings: tuple[RankingInput, ...]
    stability_report: StabilityInput | None
    decision: DecisionInput | None
    receipt_id: Id | None


class BenchmarkCounts(FrozenModel):
    """Numerators and denominators; reporting owns ratios and confidence intervals."""

    scenario_id: Id
    scenario_key: Id
    scenario_version: int
    scenario_kind: Literal["attack", "benign"]
    variant_id: Id
    attempted: int
    completed: int
    error: int
    timeout: int
    running: int
    attack_eligible: int
    attack_successes: int
    benign_eligible: int
    benign_successes: int
    false_block_eligible: int
    false_blocks: int


class RunSample(FrozenModel):
    """Raw samples retain NULL measurements and explicit skipped perturbations."""

    run_id: Id
    status: RunStatus
    scenario_id: Id
    scenario_key: Id
    scenario_version: int
    scenario_kind: Literal["attack", "benign"]
    variant_id: Id
    latency_ms: Money | None
    llm_cost_micro_usd: Money | None
    perturbation_state: str | None
    stable: bool | None
