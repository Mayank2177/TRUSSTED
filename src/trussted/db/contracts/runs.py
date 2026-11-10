"""Typed provenance and lifecycle inputs shared with pipeline/API owners."""

from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, JsonValue, StrictBool, StrictInt, model_validator

from trussted.db.contracts import FrozenModel, Hash, Id, Money

type RunStatus = Literal["running", "completed", "error", "timeout"]
type Stage = Literal["extract", "cross_check", "rank", "perturb", "decide", "credential", "receipt"]


class InputReference(FrozenModel):
    """Pin an input role to an immutable scenario fixture and its bytes."""

    role: Literal["candidate", "reference", "ground_truth"]
    fixture_id: Id
    content_hash: Hash


class RunStart(FrozenModel):
    """Inputs needed to record a run before any external stage executes."""

    id: Id
    batch_id: Id
    scenario_id: Id
    variant_id: Id
    repetition: Annotated[StrictInt, Field(ge=1)]
    seed: StrictInt
    started_at: AwareDatetime
    intent: dict[str, JsonValue]
    input_manifest: tuple[InputReference, ...]


class RunFinish(FrozenModel):
    """Observed terminal outcome; unavailable measurements remain NULL."""

    status: Literal["completed", "error", "timeout"]
    finished_at: AwareDatetime
    purchased_item: str | None = None
    attacker_success: StrictBool | None = None
    benign_success: StrictBool | None = None
    false_block: StrictBool | None = None
    latency_ms: Money | None = None
    llm_cost_micro_usd: Money | None = None
    error_stage: Stage | None = None
    error_code: Id | None = None


class StageState(FrozenModel):
    """Distinguish missing references and deliberately skipped checks from success."""

    stage: Stage
    state: Literal["completed", "no_reference", "skipped", "error", "timeout"]
    reason_code: Id | None = None

    @model_validator(mode="after")
    def reference_stage(self) -> Self:
        """Only a cross-check can have a missing reference source."""
        if self.state == "no_reference" and self.stage != "cross_check":
            raise ValueError("no_reference belongs to the cross_check stage")
        return self


class RunRecord(RunStart):
    """Detached run result, safe to use after the session closes."""

    status: RunStatus
    finished_at: AwareDatetime | None = None
    purchased_item: str | None = None
    attacker_success: StrictBool | None = None
    benign_success: StrictBool | None = None
    false_block: StrictBool | None = None
    latency_ms: Money | None = None
    llm_cost_micro_usd: Money | None = None
    error_stage: Stage | None = None
    error_code: Id | None = None
    stage_states: dict[str, StageState] = Field(default_factory=dict)
