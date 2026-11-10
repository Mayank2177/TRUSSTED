"""Bounded API reads and portable benchmark counts over all retained attempts."""

import json

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from trussted.db.base import Base
from trussted.db.contracts import FrozenModel
from trussted.db.contracts.evidence import (
    FactConflictInput,
    ObservationInput,
    ProductFactInput,
    RankingInput,
)
from trussted.db.contracts.outcomes import DecisionInput, StabilityInput
from trussted.db.contracts.queries import BenchmarkCounts, RunDetail, RunFilter, RunPage, RunSample
from trussted.db.contracts.registry import ScenarioInput, VariantInput
from trussted.db.repositories.runs import get_run, require_run
from trussted.db.tables.evidence import FactConflictRow, ObservationRow, ProductFactRow, RankingRow
from trussted.db.tables.outcomes import DecisionRow, StabilityRow
from trussted.db.tables.receipts import ReceiptRow
from trussted.db.tables.registry import ScenarioRow, VariantRow
from trussted.db.tables.runs import RunRow


def _convert[T: FrozenModel](
    row: Base,
    model: type[T],
    json_fields: tuple[str, ...] = (),
) -> T:
    """Validate storage bytes at the detached result boundary."""
    data = {column.name: getattr(row, column.name) for column in row.__table__.columns}
    for name in json_fields:
        data[name] = json.loads(data[name])
    return model.model_validate(data)


def list_runs(
    session: Session,
    filters: RunFilter,
    *,
    limit: int = 50,
    offset: int = 0,
) -> RunPage:
    """Return a bounded page with deterministic ordering even for equal timestamps."""
    if isinstance(limit, bool) or isinstance(offset, bool) or not 1 <= limit <= 100 or offset < 0:
        raise ValueError("Use limit 1..100 and a nonnegative offset")
    conditions = [
        getattr(RunRow, name) == value
        for name, value in filters.model_dump().items()
        if value is not None
    ]
    rows = session.scalars(
        select(RunRow)
        .where(*conditions)
        .order_by(RunRow.started_at, RunRow.id)
        .limit(limit)
        .offset(offset)
    ).all()
    total = session.scalar(select(func.count()).select_from(RunRow).where(*conditions)) or 0
    return RunPage(
        items=tuple(get_run(session, row.id) for row in rows),
        total=total,
        limit=limit,
        offset=offset,
    )


def get_run_detail(session: Session, run_id: str) -> RunDetail:
    """Load all evidence as DTOs; callers may close the Session immediately."""
    row = require_run(session, run_id)
    scenario = session.get(ScenarioRow, row.scenario_id)
    variant = session.get(VariantRow, row.variant_id)
    assert scenario is not None and variant is not None
    observations = session.scalars(
        select(ObservationRow).where(ObservationRow.run_id == run_id).order_by(ObservationRow.id)
    )
    facts = session.scalars(
        select(ProductFactRow).where(ProductFactRow.run_id == run_id).order_by(ProductFactRow.id)
    )
    conflicts = session.scalars(
        select(FactConflictRow)
        .join(ProductFactRow, FactConflictRow.fact_id == ProductFactRow.id)
        .where(ProductFactRow.run_id == run_id)
        .order_by(FactConflictRow.id)
    )
    rankings = session.scalars(
        select(RankingRow).where(RankingRow.run_id == run_id).order_by(RankingRow.id)
    )
    stability = session.scalar(select(StabilityRow).where(StabilityRow.run_id == run_id))
    decision = session.scalar(select(DecisionRow).where(DecisionRow.run_id == run_id))
    return RunDetail(
        run=get_run(session, run_id),
        scenario=_convert(scenario, ScenarioInput, ("definition",)),
        variant=_convert(variant, VariantInput, ("config",)),
        observations=tuple(_convert(item, ObservationInput) for item in observations),
        product_facts=tuple(
            _convert(item, ProductFactInput, ("spec", "source_span")) for item in facts
        ),
        fact_conflicts=tuple(
            _convert(item, FactConflictInput, ("extracted_value", "reference_value"))
            for item in conflicts
        ),
        rankings=tuple(
            _convert(item, RankingInput, ("ordered_fact_ids", "scores")) for item in rankings
        ),
        stability_report=_convert(stability, StabilityInput, ("winner_counts", "flips"))
        if stability
        else None,
        decision=_convert(decision, DecisionInput, ("reasons",)) if decision else None,
        receipt_id=session.scalar(select(ReceiptRow.id).where(ReceiptRow.run_id == run_id)),
    )


def _count(condition: ColumnElement[bool], name: str) -> ColumnElement[int]:
    return func.sum(case((condition, 1), else_=0)).label(name)


def _metric_columns() -> list[ColumnElement[int]]:
    completed = RunRow.status == "completed"
    attack = and_(completed, ScenarioRow.kind == "attack", RunRow.attacker_success.is_not(None))
    benign = and_(completed, ScenarioRow.kind == "benign", RunRow.benign_success.is_not(None))
    false_block = and_(completed, ScenarioRow.kind == "benign", RunRow.false_block.is_not(None))
    return [
        _count(RunRow.status.in_(["completed", "error", "timeout"]), "attempted"),
        _count(completed, "completed"),
        _count(RunRow.status == "error", "error"),
        _count(RunRow.status == "timeout", "timeout"),
        _count(RunRow.status == "running", "running"),
        _count(attack, "attack_eligible"),
        _count(and_(attack, RunRow.attacker_success.is_(True)), "attack_successes"),
        _count(benign, "benign_eligible"),
        _count(and_(benign, RunRow.benign_success.is_(True)), "benign_successes"),
        _count(false_block, "false_block_eligible"),
        _count(and_(false_block, RunRow.false_block.is_(True)), "false_blocks"),
    ]


def get_benchmark_counts(session: Session, batch_id: str) -> tuple[BenchmarkCounts, ...]:
    """Return explicit counts grouped by exact scenario revision and variant."""
    statement = (
        select(
            RunRow.scenario_id,
            ScenarioRow.scenario_key,
            ScenarioRow.version.label("scenario_version"),
            ScenarioRow.kind.label("scenario_kind"),
            RunRow.variant_id,
            *_metric_columns(),
        )
        .join(ScenarioRow, RunRow.scenario_id == ScenarioRow.id)
        .where(RunRow.batch_id == batch_id)
    )
    statement = statement.group_by(
        RunRow.scenario_id,
        ScenarioRow.scenario_key,
        ScenarioRow.version,
        ScenarioRow.kind,
        RunRow.variant_id,
    ).order_by(ScenarioRow.scenario_key, ScenarioRow.version, RunRow.variant_id)
    return tuple(
        BenchmarkCounts.model_validate(dict(row)) for row in session.execute(statement).mappings()
    )


def get_benchmark_samples(session: Session, batch_id: str) -> tuple[RunSample, ...]:
    """Retain failed/active rows and skipped-check states for honest reports."""
    rows = session.execute(
        select(RunRow, ScenarioRow, StabilityRow)
        .join(ScenarioRow, RunRow.scenario_id == ScenarioRow.id)
        .outerjoin(StabilityRow, StabilityRow.run_id == RunRow.id)
        .where(RunRow.batch_id == batch_id)
        .order_by(RunRow.id)
    )
    samples = []
    for run, scenario, stability in rows:
        state = json.loads(run.stage_states).get("perturb", {}).get("state")
        samples.append(
            RunSample(
                run_id=run.id,
                status=run.status,
                scenario_id=run.scenario_id,
                scenario_key=scenario.scenario_key,
                scenario_version=scenario.version,
                scenario_kind=scenario.kind,
                variant_id=run.variant_id,
                latency_ms=run.latency_ms,
                llm_cost_micro_usd=run.llm_cost_micro_usd,
                perturbation_state=state,
                stable=stability.stable if stability is not None else None,
            )
        )
    return tuple(samples)
