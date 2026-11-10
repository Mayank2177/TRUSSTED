"""Persist stability and policy outputs alongside explicit stage completion."""

from sqlalchemy.orm import Session

from trussted.db.contracts.outcomes import DecisionInput, StabilityInput
from trussted.db.contracts.runs import StageState
from trussted.db.errors import InvalidEvidence, InvalidTransition, flush
from trussted.db.repositories.runs import record_stage_state, require_run
from trussted.db.tables.evidence import ProductFactRow
from trussted.db.tables.outcomes import DecisionRow, StabilityRow
from trussted.db.values import canonical_json


def _require_running(session: Session, run_id: str) -> None:
    if require_run(session, run_id).status != "running":
        raise InvalidTransition("Outcomes cannot be added to a terminal run")


def save_stability_report(session: Session, value: StabilityInput) -> str:
    """Store one final report; skipped or failed stages remain explicitly distinct."""
    _require_running(session, value.run_id)
    for fact_id in value.winner_counts:
        fact = session.get(ProductFactRow, fact_id)
        if fact is None or fact.run_id != value.run_id:
            raise InvalidEvidence("Stability winners must be facts from the same run")
    row = StabilityRow(
        **(
            value.model_dump()
            | {
                "winner_counts": canonical_json(dict(value.winner_counts)),
                "flips": canonical_json(value.flips),
            }
        )
    )
    record_stage_state(session, value.run_id, StageState(stage="perturb", state="completed"))
    session.add(row)
    flush(session)
    return value.id


def save_decision(session: Session, value: DecisionInput) -> str:
    """Store an owner-evaluated decision without replacing an earlier policy result."""
    _require_running(session, value.run_id)
    row = DecisionRow(**(value.model_dump() | {"reasons": canonical_json(list(value.reasons))}))
    record_stage_state(session, value.run_id, StageState(stage="decide", state="completed"))
    session.add(row)
    flush(session)
    return value.id
