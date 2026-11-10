"""Anthropic adapter (optional dependency: ``pip install trussted[anthropic]``).

Forces a single tool call so the model must return schema-shaped JSON. NOTE: not exercised
against the live API in this repo's tests; verify with a real key before relying on it.
"""

from __future__ import annotations

import os
from typing import Any

from ..config import LLMConfig
from ..errors import ConfigError, LLMError, LLMResponseError, LLMTransientError
from .base import LLMRequest, LLMResponse

_TOOL_NAME = "record_products"
_TRANSIENT = frozenset(
    {"APIConnectionError", "APITimeoutError", "RateLimitError", "InternalServerError"}
)


class AnthropicClient:
    def __init__(self, config: LLMConfig, *, client: Any | None = None) -> None:
        if not config.model:
            raise ConfigError("LLMConfig.model is required (set TRUSSTED_LLM_MODEL)")
        self._config = config
        if client is None:
            try:
                import anthropic
            except ImportError as exc:
                raise ConfigError("install the extra: pip install trussted[anthropic]") from exc
            key = os.environ.get(config.api_key_env)
            if not key:
                raise ConfigError(f"environment variable {config.api_key_env} is not set")
            client = anthropic.Anthropic(api_key=key)
        self._client = client

    def complete_json(self, request: LLMRequest) -> LLMResponse:
        try:
            message = self._client.with_options(timeout=request.timeout_s, max_retries=0).messages.create(
                model=self._config.model,
                max_tokens=self._config.max_tokens,
                temperature=0,
                system=request.system,
                messages=[{"role": "user", "content": request.user}],
                tools=[{"name": _TOOL_NAME, "description": "Record the extracted products.",
                        "input_schema": dict(request.schema)}],
                tool_choice={"type": "tool", "name": _TOOL_NAME},
            )
        except Exception as exc:  # noqa: BLE001 - SDK exception types are not imported here
            transient = any(c.__name__ in _TRANSIENT for c in type(exc).__mro__)
            raise (LLMTransientError if transient else LLMError)(
                f"{type(exc).__name__}: {exc}"
            ) from exc
        for block in getattr(message, "content", []) or []:
            if getattr(block, "type", None) == "tool_use" and getattr(block, "name", "") == _TOOL_NAME:
                usage = getattr(message, "usage", None)
                return LLMResponse(
                    data=block.input,
                    model=str(getattr(message, "model", self._config.model)),
                    input_tokens=getattr(usage, "input_tokens", None),
                    output_tokens=getattr(usage, "output_tokens", None),
                )
        raise LLMResponseError("model returned no tool_use block")
