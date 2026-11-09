"""Canonical representations used for database text, hashes and timestamps."""

import hashlib
from datetime import UTC, datetime

import rfc8785
from pydantic import JsonValue


def canonical_json(value: JsonValue) -> str:
    """Serialize finite interoperable JSON with the RFC 8785 implementation."""
    return rfc8785.dumps(value).decode("utf-8")


def sha256_hex(data: bytes) -> str:
    """Return lowercase SHA-256 hex over exact bytes."""
    return hashlib.sha256(data).hexdigest()


def utc_datetime(value: datetime) -> datetime:
    """Normalize an aware datetime to UTC and reject ambiguous naive values."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone")
    return value.astimezone(UTC)


def utc_text(value: datetime) -> str:
    """Format UTC with six fractional digits and an unambiguous Z suffix."""
    return utc_datetime(value).isoformat(timespec="microseconds").replace("+00:00", "Z")
