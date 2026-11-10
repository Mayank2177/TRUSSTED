"""Validated values shared by persistence inputs and detached read results."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints

Id = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=255)]
Hash = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]
Money = Annotated[StrictInt, Field(ge=0)]
Currency = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Z]{3}$")]


class FrozenModel(BaseModel):
    """Closed, immutable boundary model that can read detached row attributes."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
