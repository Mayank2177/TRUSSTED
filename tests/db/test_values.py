"""Canonical values reject ambiguities before they enter persisted evidence."""

import json
from datetime import UTC, datetime, timedelta, timezone

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import TypeAdapter, ValidationError

from trussted.db.contracts import Currency, Hash, Id, Money
from trussted.db.values import canonical_json, sha256_hex, utc_datetime, utc_text


def test_canonical_json_and_hash() -> None:
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert sha256_hex(b"abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_utc_normalizes_fixed_precision_and_rejects_naive() -> None:
    value = datetime(2026, 1, 2, 6, 34, 5, 123, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    assert utc_text(value) == "2026-01-02T01:04:05.000123Z"
    assert utc_datetime(value) == datetime(2026, 1, 2, 1, 4, 5, 123, tzinfo=UTC)
    with pytest.raises(ValueError):
        utc_text(datetime(2026, 1, 2))
    with pytest.raises(ValueError):
        utc_datetime(datetime(2026, 1, 2))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_json_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        canonical_json({"value": value})


@pytest.mark.parametrize("value", ["a" * 63, "A" * 64, "g" * 64, ""])
def test_hash_validation(value: str) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(Hash).validate_python(value)


@pytest.mark.parametrize("value", [True, -1, 1.0])
def test_money_is_strict_nonnegative_integer(value: object) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(Money).validate_python(value)


def test_identifier_and_currency_boundaries() -> None:
    assert TypeAdapter(Money).validate_python(0) == 0
    for value in ["", "x" * 256]:
        with pytest.raises(ValidationError):
            TypeAdapter(Id).validate_python(value)
    for value in ["usd", "US", "USDD"]:
        with pytest.raises(ValidationError):
            TypeAdapter(Currency).validate_python(value)


json_values = st.recursive(
    st.none()
    | st.booleans()
    | st.integers(-(2**53) + 1, 2**53 - 1)
    | st.floats(min_value=-(2**53) + 1, max_value=2**53 - 1, allow_nan=False, allow_infinity=False)
    | st.text(alphabet=st.characters(blacklist_categories=("Cs",))),
    lambda children: (
        st.lists(children, max_size=5)
        | st.dictionaries(
            st.text(alphabet=st.characters(blacklist_categories=("Cs",))), children, max_size=5
        )
    ),
    max_leaves=10,
)


@given(json_values)
def test_canonicalization_is_idempotent(value: object) -> None:
    # JsonValue is recursively enforced at the public model boundary.
    from pydantic import JsonValue

    validated = TypeAdapter(JsonValue).validate_python(value)
    encoded = canonical_json(validated)
    assert canonical_json(json.loads(encoded)) == encoded
