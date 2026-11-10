"""Minimal HTTPS JSON transport (stdlib only) with an injectable interface for tests."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlsplit

from ..errors import IntegrationError, TransientIntegrationError

logger = logging.getLogger(__name__)
MAX_BODY_BYTES = 5_000_000
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


class TransportError(Exception):
    """Network-level failure (DNS, connect, timeout)."""


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    body: bytes


class HttpTransport(Protocol):
    def send(self, method: str, url: str, headers: Mapping[str, str], body: bytes | None,
             timeout_s: float) -> HttpResponse: ...


class UrllibTransport:
    """HTTPS only. Non-2xx statuses are returned, not raised."""

    def send(self, method: str, url: str, headers: Mapping[str, str], body: bytes | None,
             timeout_s: float) -> HttpResponse:
        if urlsplit(url).scheme != "https":
            raise IntegrationError("only https URLs are allowed")
        request = urllib.request.Request(url, data=body, method=method, headers=dict(headers))  # noqa: S310
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as resp:  # noqa: S310
                return HttpResponse(resp.status, resp.read(MAX_BODY_BYTES + 1)[:MAX_BODY_BYTES])
        except urllib.error.HTTPError as exc:
            return HttpResponse(exc.code, exc.read(MAX_BODY_BYTES))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise TransportError(f"{type(exc).__name__}: {exc}") from exc


def send_json(
    transport: HttpTransport, method: str, url: str, *, headers: Mapping[str, str],
    payload: Any | None = None, raw_body: bytes | None = None, timeout_s: float,
    retries: int, backoff_s: float, sleep: Callable[[float], None] = time.sleep,
) -> tuple[int, Any]:
    """Send a request, retrying transient failures. Returns (status, parsed JSON or None).

    Callers decide how to treat non-2xx statuses that are not retryable. Retried statuses that
    never recover raise ``TransientIntegrationError``. Never logs headers or bodies.
    """
    body = raw_body if raw_body is not None else (
        None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    attempt = 0
    while True:
        try:
            resp = transport.send(method, url, headers, body, timeout_s)
            failure = f"HTTP {resp.status}" if resp.status in RETRY_STATUSES else None
        except TransportError as exc:
            resp, failure = None, str(exc)
        if failure is None and resp is not None:
            break
        if attempt >= retries:
            raise TransientIntegrationError(f"{method} {urlsplit(url).path}: {failure}")
        logger.warning("retrying %s %s (%s)", method, urlsplit(url).path, failure)
        sleep(backoff_s * (2**attempt))
        attempt += 1
    if not resp.body:
        return resp.status, None
    try:
        return resp.status, json.loads(resp.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        if 200 <= resp.status < 300:
            raise IntegrationError(f"{method} {urlsplit(url).path}: invalid JSON response") from exc
        return resp.status, None
