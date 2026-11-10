"""Spec value parsing/normalisation (e.g. ``"1 TB"`` -> 1_000_000_000_000 bytes)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Literal

from .money import parse_amount
from ..errors import ValidationError

SpecOp = Literal["eq", "gte", "lte", "in"]


def _d(x: str) -> Decimal:
    return Decimal(x)


# Case-insensitive. Data units are SI (1 TB = 10^12 bytes) unless suffixed ``ib`` (binary).
# Bits vs bytes (``Mb`` vs ``MB``) are NOT distinguished and "b" alone is unsupported.
_UNITS: Mapping[str, tuple[str, Decimal]] = MappingProxyType({
    "byte": ("data", _d("1")), "bytes": ("data", _d("1")),
    "kb": ("data", _d("1e3")), "mb": ("data", _d("1e6")), "gb": ("data", _d("1e9")),
    "tb": ("data", _d("1e12")), "pb": ("data", _d("1e15")),
    "kib": ("data", _d(2**10)), "mib": ("data", _d(2**20)), "gib": ("data", _d(2**30)),
    "tib": ("data", _d(2**40)),
    "mm": ("length", _d("0.001")), "cm": ("length", _d("0.01")), "m": ("length", _d("1")),
    "km": ("length", _d("1000")), "in": ("length", _d("0.0254")), "inch": ("length", _d("0.0254")),
    "inches": ("length", _d("0.0254")), "ft": ("length", _d("0.3048")),
    "g": ("mass", _d("0.001")), "kg": ("mass", _d("1")), "lb": ("mass", _d("0.45359237")),
    "lbs": ("mass", _d("0.45359237")), "oz": ("mass", _d("0.028349523125")),
    "w": ("power", _d("1")), "kw": ("power", _d("1000")),
    "wh": ("energy", _d("1")), "kwh": ("energy", _d("1000")),
    "mah": ("charge", _d("1")), "ah": ("charge", _d("1000")),
    "hz": ("frequency", _d("1")), "khz": ("frequency", _d("1e3")),
    "mhz": ("frequency", _d("1e6")), "ghz": ("frequency", _d("1e9")),
})

_QTY_RE = re.compile(r"^\s*(\d[\d,]*(?:\.\d+)?)\s*([A-Za-z]+)?\s*$")
_MAX_SPEC_CHARS = 200


@dataclass(frozen=True, slots=True)
class SpecValue:
    """Either a dimensioned quantity (base units) or normalised text."""

    kind: Literal["quantity", "text"]
    text: str
    dimension: str | None = None
    number: Decimal | None = None


def normalize_text(raw: str) -> str:
    return " ".join(raw.casefold().split())


def parse_spec_value(raw: str) -> SpecValue:
    if not isinstance(raw, str):
        raise ValidationError("spec value must be a string")
    if len(raw) > _MAX_SPEC_CHARS:
        raise ValidationError("spec value too long")
    text = normalize_text(raw)
    match = _QTY_RE.match(raw)
    if match:
        number_text, unit = match.group(1), match.group(2)
        try:
            number = parse_amount(number_text)
        except ValidationError:
            return SpecValue("text", text)
        if unit is None:
            return SpecValue("quantity", text, "number", number)
        entry = _UNITS.get(unit.casefold())
        if entry is not None:
            return SpecValue("quantity", text, entry[0], number * entry[1])
    return SpecValue("text", text)


def spec_equal(a: SpecValue, b: SpecValue) -> bool:
    if a.kind != b.kind:
        return False
    if a.kind == "quantity":
        return a.dimension == b.dimension and a.number == b.number
    return a.text == b.text


def spec_matches(op: SpecOp, actual: SpecValue, expected: tuple[SpecValue, ...]) -> bool | None:
    """Evaluate a constraint. Returns None when the values are not comparable."""
    if not expected:
        raise ValidationError("constraint has no expected values")
    if op in ("eq", "in"):
        return any(spec_equal(actual, e) for e in expected)
    target = expected[0]
    if (actual.kind != "quantity" or target.kind != "quantity"
            or actual.dimension != target.dimension):
        return None
    assert actual.number is not None and target.number is not None
    return actual.number >= target.number if op == "gte" else actual.number <= target.number
