"""LLM provider interface. Everything else depends on this Protocol, never on an SDK."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class LLMRequest:
    system: str
    user: str
    schema: Mapping[str, Any]
    seed: int | None
    timeout_s: float


@dataclass(frozen=True, slots=True)
class LLMResponse:
    data: Any
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


@runtime_checkable
class LLMClient(Protocol):
    def complete_json(self, request: LLMRequest) -> LLMResponse:
        """Return JSON conforming to ``request.schema``. Raise ``LLMError`` subclasses on failure."""
        ...
