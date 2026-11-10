"""Caller-supplied, versioned benchmark registry inputs."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, JsonValue, StrictInt, field_validator

from warrant.db.contracts import FrozenModel, Hash, Id
from warrant.db.values import canonical_json


class ScenarioInput(FrozenModel):
    id: Id
    scenario_key: Id
    title: Annotated[str, Field(min_length=1)]
    kind: Literal["attack", "benign"]
    attack_type: str | None = None
    definition: JsonValue
    expected_outcome: Annotated[str, Field(min_length=1)]
    version: Annotated[StrictInt, Field(ge=1)]

    @field_validator("definition")
    @classmethod
    def canonical_definition(cls, value: JsonValue) -> JsonValue:
        canonical_json(value)
        return value


class FixtureInput(FrozenModel):
    id: Id
    scenario_id: Id
    name: Id
    content_hash: Hash
    path: Annotated[str, Field(min_length=1)]
    created_at: AwareDatetime


class VariantInput(FrozenModel):
    id: Id
    name: Id
    model_name: Id
    model_version: Id
    prompt_version: Id
    config: JsonValue
    config_hash: Hash | None = None

    @field_validator("config")
    @classmethod
    def canonical_config(cls, value: JsonValue) -> JsonValue:
        canonical_json(value)
        return value


class BatchInput(FrozenModel):
    id: Id
    created_at: AwareDatetime
    git_commit: Annotated[str, Field(min_length=1)]
    seed: StrictInt
    notes: str | None = None
