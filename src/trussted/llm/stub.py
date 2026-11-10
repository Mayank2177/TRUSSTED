"""Deterministic clients for tests and replay."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from ..errors import ConfigError, LLMError, LLMResponseError
from .base import LLMClient, LLMRequest, LLMResponse

Responder = Callable[[LLMRequest], Any]


class StubClient:
    """Returns canned outputs in order (or from a callable). Records every request.

    An item may be an Exception instance, which is raised instead of returned.
    """

    def __init__(self, responses: Sequence[Any] | Responder, model: str = "stub") -> None:
        self._responses = responses
        self._model = model
        self._index = 0
        self._lock = threading.Lock()
        self.requests: list[LLMRequest] = []

    def complete_json(self, request: LLMRequest) -> LLMResponse:
        with self._lock:
            self.requests.append(request)
            if callable(self._responses):
                item = self._responses(request)
            else:
                if self._index >= len(self._responses):
                    raise LLMResponseError("StubClient exhausted")
                item = self._responses[self._index]
                self._index += 1
        if isinstance(item, Exception):
            raise item
        return LLMResponse(data=copy.deepcopy(item), model=self._model)


def request_key(request: LLMRequest) -> str:
    payload = json.dumps(
        {"system": request.system, "user": request.user, "schema": request.schema,
         "seed": request.seed},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CassetteClient:
    """Replays recorded responses; optionally records misses from a live client."""

    _VERSION = 1

    def __init__(self, path: str | Path, *, record_with: LLMClient | None = None) -> None:
        self._path = Path(path)
        self._live = record_with
        self._lock = threading.Lock()
        self._entries: dict[str, dict[str, Any]] = {}
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ConfigError(f"unreadable cassette {self._path}: {exc}") from exc
            if raw.get("version") != self._VERSION or not isinstance(raw.get("entries"), dict):
                raise ConfigError(f"unsupported cassette format: {self._path}")
            self._entries = raw["entries"]
        elif record_with is None:
            raise ConfigError(f"cassette not found and not recording: {self._path}")

    def complete_json(self, request: LLMRequest) -> LLMResponse:
        key = request_key(request)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                if self._live is None:
                    raise LLMResponseError(f"no cassette entry for request {key[:12]}")
                response = self._live.complete_json(request)
                self._entries[key] = {"data": response.data, "model": response.model}
                self._flush()
                return response
        return LLMResponse(data=copy.deepcopy(entry["data"]), model=str(entry.get("model", "")))

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        body = json.dumps({"version": self._VERSION, "entries": self._entries}, indent=2,
                          sort_keys=True, ensure_ascii=False)
        fd, tmp = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(body)
            os.replace(tmp, self._path)
        except OSError as exc:
            Path(tmp).unlink(missing_ok=True)
            raise LLMError(f"cannot write cassette: {exc}") from exc
