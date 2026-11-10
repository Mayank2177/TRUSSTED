"""Identifier helpers."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from ..errors import ValidationError

_GTIN_LENGTHS = frozenset({8, 12, 13, 14})


def normalize_gtin(raw: str) -> str | None:
    """Return a checksum-valid GTIN (digits only) or None."""
    if not isinstance(raw, str):
        return None
    digits = re.sub(r"[\s-]", "", raw)
    if not digits.isascii() or not digits.isdigit() or len(digits) not in _GTIN_LENGTHS:
        return None
    body, check = digits[:-1], int(digits[-1])
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return digits if (10 - total % 10) % 10 == check else None


def merchant_id_from_url(url: str) -> str:
    """Derive a stable merchant id (lowercase ASCII host, no leading ``www.``)."""
    if not isinstance(url, str) or not url.strip():
        raise ValidationError("url must be a non-empty string")
    try:
        parts = urlsplit(url.strip())
        host = parts.hostname
    except ValueError as exc:
        raise ValidationError(f"invalid url: {exc}") from exc
    if parts.scheme not in ("http", "https") or not host:
        raise ValidationError("url must be http(s) with a host")
    host = host.rstrip(".")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValidationError("invalid host") from exc
    return host.removeprefix("www.")
