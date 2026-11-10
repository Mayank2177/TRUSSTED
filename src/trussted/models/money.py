"""Exact money arithmetic in minor units. Floats are never used for money."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from functools import total_ordering

from ..errors import ValidationError

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
# ISO 4217 currencies whose minor-unit exponent is not 2. Others default to 2.
_ZERO_DECIMAL = frozenset(
    "BIF CLP DJF GNF ISK JPY KMF KRW PYG RWF UGX UYI VND VUV XAF XOF XPF".split()
)
_THREE_DECIMAL = frozenset("BHD IQD JOD KWD LYD OMR TND".split())

_PLAIN_AMOUNT = re.compile(r"^\d+(\.\d+)?$")
_GROUPED_AMOUNT = re.compile(r"^\d{1,3}(,\d{3})+(\.\d+)?$")
_MAX_AMOUNT_CHARS = 24


def currency_exponent(code: str) -> int:
    if not isinstance(code, str) or not _CURRENCY_RE.fullmatch(code):
        raise ValidationError(f"invalid currency code: {code!r}")
    if code in _ZERO_DECIMAL:
        return 0
    if code in _THREE_DECIMAL:
        return 3
    return 2


def parse_amount(text: str) -> Decimal:
    """Parse a plain or US-grouped non-negative decimal string. Ambiguous formats are rejected.

    Accepts ``"99"``, ``"99.50"``, ``"1,299.99"``. Rejects ``"1.299,99"``, ``"1e5"``, ``"$5"``.
    """
    if not isinstance(text, str):
        raise ValidationError("amount must be a string")
    s = text.strip()
    if not s or len(s) > _MAX_AMOUNT_CHARS:
        raise ValidationError(f"invalid amount: {text!r}")
    if _GROUPED_AMOUNT.match(s):
        s = s.replace(",", "")
    elif not _PLAIN_AMOUNT.match(s):
        raise ValidationError(f"invalid amount: {text!r}")
    try:
        return Decimal(s)
    except InvalidOperation as exc:  # pragma: no cover - regex guards this
        raise ValidationError(f"invalid amount: {text!r}") from exc


@total_ordering
@dataclass(frozen=True, slots=True)
class Money:
    """Integer minor units plus ISO 4217 currency. Cross-currency operations raise."""

    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        if isinstance(self.amount_minor, bool) or not isinstance(self.amount_minor, int):
            raise ValidationError("amount_minor must be an int")
        currency_exponent(self.currency)  # validates

    @classmethod
    def from_decimal(cls, amount: Decimal, currency: str) -> Money:
        exp = currency_exponent(currency)
        if not isinstance(amount, Decimal) or not amount.is_finite():
            raise ValidationError("amount must be a finite Decimal")
        scaled = amount.scaleb(exp)
        if scaled != scaled.to_integral_value():
            raise ValidationError(f"{amount} has more fractional digits than {currency} allows")
        return cls(int(scaled), currency)

    def to_decimal(self) -> Decimal:
        return Decimal(self.amount_minor).scaleb(-currency_exponent(self.currency))

    def _same(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValidationError(f"currency mismatch: {self.currency} vs {other.currency}")

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._same(other)
        return self.amount_minor < other.amount_minor

    def __add__(self, other: object) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._same(other)
        return Money(self.amount_minor + other.amount_minor, self.currency)

    def __mul__(self, factor: object) -> Money:
        if isinstance(factor, bool) or not isinstance(factor, int):
            return NotImplemented
        return Money(self.amount_minor * factor, self.currency)

    __rmul__ = __mul__

    def amount_str(self) -> str:
        """Plain amount with the currency's exact decimals, e.g. ``"89.99"`` (for APIs)."""
        return f"{self.to_decimal():.{currency_exponent(self.currency)}f}"

    def __str__(self) -> str:
        exp = currency_exponent(self.currency)
        return f"{self.to_decimal():.{exp}f} {self.currency}"
