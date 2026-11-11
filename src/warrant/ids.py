"""Application-generated UUIDv7 identifiers, compatible with DATABASE.md."""

from __future__ import annotations

import secrets
import time
import uuid


def uuid7() -> str:
    """Return a UUIDv7 string using the current Unix time in milliseconds."""
    timestamp_ms = time.time_ns() // 1_000_000
    if timestamp_ms >= 1 << 48:
        raise OverflowError("timestamp is outside the UUIDv7 range")
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)
    value = (timestamp_ms << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    return str(uuid.UUID(int=value))
