"""Validated final stability and policy outputs; evaluation belongs to pipeline owners."""

from typing import Annotated, Literal

from pydantic import Field, JsonValue, StrictBool, field_validator

from warrant.db.contracts import Currency, FrozenModel, Id, Money
from warrant.db.values import canonical_json


class StabilityInput(FrozenModel):
    """One final stability result; winner identities are facts from this run."""

    id: Id
    run_id: Id
    winner_counts: dict[Id, Money]
    stable: StrictBool
    threshold: Annotated[float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)]
    flips: dict[str, JsonValue] | list[JsonValue]

    @field_validator("flips")
    @classmethod
    def canonical_flips(
        cls,
        value: dict[str, JsonValue] | list[JsonValue],
    ) -> dict[str, JsonValue] | list[JsonValue]:
        """Retain the owner's structured flip evidence in canonical JSON."""
        canonical_json(value)
        return value


class DecisionInput(FrozenModel):
    """A policy result and its reason codes; storage never invents an ALLOW."""

    id: Id
    run_id: Id
    result: Literal["ALLOW", "STEP_UP", "BLOCK"]
    reasons: tuple[Id, ...]
    policy_version: Id
    amount_minor: Money
    currency: Currency
