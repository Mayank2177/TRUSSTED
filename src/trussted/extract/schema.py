"""JSON Schema for the extraction tool call."""

from __future__ import annotations

from typing import Any

CONDITIONS = ("new", "used", "refurbished", "unknown")


def product_list_schema(max_products: int) -> dict[str, Any]:
    nullable_str = {"type": ["string", "null"]}
    return {
        "type": "object",
        "properties": {
            "products": {
                "type": "array",
                "maxItems": max_products,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "brand": nullable_str,
                        "sku": nullable_str,
                        "gtin": nullable_str,
                        "price": {"type": "string"},
                        "currency": {"type": "string"},
                        "shipping_price": nullable_str,
                        "additional_charges": nullable_str,
                        "is_recurring": {"type": ["boolean", "null"]},
                        "delivery_days": {"type": ["integer", "null"]},
                        "rating": nullable_str,
                        "review_count": {"type": ["integer", "null"]},
                        "condition": {"type": "string", "enum": list(CONDITIONS)},
                        "specs": {"type": "object", "additionalProperties": {"type": "string"}},
                        "evidence": {"type": "string"},
                    },
                    "required": ["name", "price", "currency", "evidence"],
                },
            }
        },
        "required": ["products"],
    }
