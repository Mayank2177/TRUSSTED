"""Validated extraction, cross-check and ranking evidence supplied by pipeline owners."""

from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

from trussted.db.contracts import Currency, FrozenModel, Hash, Id, Money
from trussted.db.values import canonical_json

type Score = Annotated[float, Field(strict=True, allow_inf_nan=False)]
type TextValue = Annotated[str, StringConstraints(strict=True, min_length=1)]
type Perturbation = Annotated[
    str, StringConstraints(strict=True, pattern=r"^(none|strip_persuasion|shuffle_[0-9]+)$")
]


class SourceSpan(FrozenModel):
    """Offsets in the extractor's agreed representation; storage does not reinterpret units."""

    start: Money
    end: Money

    @model_validator(mode="after")
    def ordered_offsets(self) -> Self:
        """Reject reversed offsets while preserving valid empty spans."""
        if self.end < self.start:
            raise ValueError("Source span end must be at least its start")
        return self


class ObservationInput(FrozenModel):
    """Raw content provenance; page bytes remain in the external content store."""

    id: Id
    run_id: Id
    url: TextValue
    content_hash: Hash
    byte_size: Money
    fetched_at: AwareDatetime


class ProductFactInput(FrozenModel):
    """Extracted fact with caller-supplied product identity and source offsets."""

    id: Id
    run_id: Id
    observation_id: Id
    sku: Id
    name: TextValue
    price_minor: Money
    currency: Currency
    spec: dict[str, JsonValue]
    gtin: Id | None = None
    seller_id: Id
    source_span: SourceSpan

    @field_validator("spec")
    @classmethod
    def canonical_spec(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        """Reject values the shared canonical JSON format cannot encode."""
        canonical_json(value)
        return value


class FactConflictInput(FrozenModel):
    """A reference mismatch; the cross-check owner supplies its values and severity."""

    id: Id
    fact_id: Id
    field: TextValue
    extracted_value: JsonValue
    reference_value: JsonValue
    severity: Literal["low", "medium", "high"]
    reference_source: TextValue

    @field_validator("extracted_value", "reference_value")
    @classmethod
    def canonical_value(cls, value: JsonValue) -> JsonValue:
        """Keep conflict values representable in canonical event payloads."""
        canonical_json(value)
        return value


class RankingInput(FrozenModel):
    """Preserve ranking order and scores without calculating policy or ranking."""

    id: Id
    run_id: Id
    perturbation: Perturbation
    ordered_fact_ids: tuple[Id, ...]
    scores: dict[Id, Score]
    winner_fact_id: Id | None = None

    @model_validator(mode="after")
    def consistent_candidates(self) -> Self:
        """Scores and an optional winner refer only to distinct ranked candidates."""
        candidates = set(self.ordered_fact_ids)
        if len(candidates) != len(self.ordered_fact_ids):
            raise ValueError("Ranking candidates must be distinct")
        if not set(self.scores).issubset(candidates):
            raise ValueError("Scores must refer to ranked candidates")
        if self.winner_fact_id is not None and self.winner_fact_id not in candidates:
            raise ValueError("Ranking winner must be a candidate")
        return self
