"""Strict cart model and deterministic, versioned SHA-256 cart fingerprint."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

_MAX_SAFE_INTEGER = (1 << 53) - 1


def _identifier(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be text")
    normalized = unicodedata.normalize("NFC", value).strip()
    if not normalized or any(ord(char) < 0x20 for char in normalized):
        raise ValueError(f"{field} must be non-empty text without control characters")
    return normalized


def _minor_units(value: int, field: str) -> int:
    if type(value) is not int or value < 0 or value > _MAX_SAFE_INTEGER:
        raise ValueError(f"{field} must be a safe non-negative integer in minor units")
    return value


@dataclass(frozen=True, slots=True)
class CartLine:
    product_id: str
    quantity: int
    unit_price_minor: int
    sku: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "product_id", _identifier(self.product_id, "product_id"))
        if type(self.quantity) is not int or not 1 <= self.quantity <= _MAX_SAFE_INTEGER:
            raise ValueError("quantity must be a positive safe integer")
        _minor_units(self.unit_price_minor, "unit_price_minor")
        if self.unit_price_minor * self.quantity > _MAX_SAFE_INTEGER:
            raise ValueError("line total exceeds the safe integer range")
        if self.sku is not None:
            object.__setattr__(self, "sku", _identifier(self.sku, "sku"))


@dataclass(frozen=True, slots=True)
class Cart:
    merchant_id: str
    amount_minor: int
    currency: str
    items: tuple[CartLine, ...]
    tax_minor: int = 0
    shipping_minor: int = 0
    discount_minor: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "merchant_id", _identifier(self.merchant_id, "merchant_id"))
        if not isinstance(self.currency, str) or re.fullmatch(r"[A-Z]{3}", self.currency) is None:
            raise ValueError("currency must be a three-letter uppercase ISO 4217 code")
        _minor_units(self.amount_minor, "amount_minor")
        _minor_units(self.tax_minor, "tax_minor")
        _minor_units(self.shipping_minor, "shipping_minor")
        _minor_units(self.discount_minor, "discount_minor")
        if (
            type(self.items) is not tuple
            or not self.items
            or any(not isinstance(item, CartLine) for item in self.items)
        ):
            raise ValueError("cart must contain at least one valid item")
        line_total = sum(item.quantity * item.unit_price_minor for item in self.items)
        expected = line_total + self.tax_minor + self.shipping_minor - self.discount_minor
        if expected < 0 or expected != self.amount_minor:
            raise ValueError("amount_minor must equal item totals plus tax/shipping less discounts")


def canonical_cart_bytes(cart: Cart) -> bytes:
    """Serialize only declared purchase fields with sorted ASCII keys and integer money.

    The schema is versioned independently of Python object representations. Lines are sorted
    by their complete semantic tuple so display ordering cannot alter an otherwise identical
    cart. The schema intentionally contains no floats or free-form metadata.
    """
    if not isinstance(cart, Cart):
        raise TypeError("cart must be a validated Cart")
    lines = sorted(
        cart.items,
        key=lambda line: (line.product_id, line.sku or "", line.quantity, line.unit_price_minor),
    )
    payload: dict[str, Any] = {
        "amount_minor": cart.amount_minor,
        "currency": cart.currency,
        "discount_minor": cart.discount_minor,
        "items": [
            {
                "product_id": line.product_id,
                "quantity": line.quantity,
                "sku": line.sku,
                "unit_price_minor": line.unit_price_minor,
            }
            for line in lines
        ],
        "merchant_id": cart.merchant_id,
        "schema": "warrant-cart-v1",
        "shipping_minor": cart.shipping_minor,
        "tax_minor": cart.tax_minor,
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8", errors="strict")


def cart_hash(cart: Cart) -> str:
    return hashlib.sha256(canonical_cart_bytes(cart)).hexdigest()
