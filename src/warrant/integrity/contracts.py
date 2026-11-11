"""Typed hand-off contracts for Stages 1–3 and Stage 4.

The upstream stages may adapt their concrete Pydantic/ORM models to these boundary types;
Stage 4 deliberately does not own extraction, verification, or ranking behavior.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol


class ContentKind(StrEnum):
    FACT = "fact"
    STRUCTURED = "structured"
    MARKETING = "marketing"
    REVIEW = "review"
    UNCLASSIFIED = "unclassified"


@dataclass(frozen=True, slots=True)
class ObservationBlock:
    kind: ContentKind
    text: str
    # Structured source fields stay separate from prose so stripping cannot erase them.
    structured_data: Mapping[str, str | int | bool | None] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ContentKind) or not isinstance(self.text, str):
            raise ValueError("observation block requires a known kind and text")
        if self.structured_data is None:
            return
        if not isinstance(self.structured_data, Mapping):
            raise ValueError("structured_data must be a mapping")
        copied = dict(self.structured_data)
        if any(
            not isinstance(key, str)
            or not key
            or (value is not None and type(value) not in (str, int, bool))
            for key, value in copied.items()
        ):
            raise ValueError("structured fields require non-empty keys and scalar JSON values")
        object.__setattr__(self, "structured_data", MappingProxyType(copied))


def canonical_observation_hash(blocks: tuple[ObservationBlock, ...]) -> str:
    """Hash typed visible content with kind, structured values, and original block order."""
    if not isinstance(blocks, tuple) or any(
        not isinstance(block, ObservationBlock) for block in blocks
    ):
        raise ValueError("blocks must be a tuple of validated ObservationBlock values")
    content = {
        "schema": "warrant-observation-content-v1",
        "blocks": [
            {
                "kind": block.kind.value,
                "text": block.text,
                "structured_data": (
                    dict(block.structured_data) if block.structured_data is not None else None
                ),
            }
            for block in blocks
        ],
    }
    serialized = json.dumps(
        content,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8", errors="strict")
    return hashlib.sha256(serialized).hexdigest()


@dataclass(frozen=True, slots=True)
class CandidateObservation:
    candidate_id: str
    observation_id: str
    source_uri: str
    content_hash: str
    blocks: tuple[ObservationBlock, ...]
    source_content_hash: str | None = None

    def __post_init__(self) -> None:
        for name in ("candidate_id", "observation_id", "source_uri"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")
        if (
            not isinstance(self.content_hash, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.content_hash) is None
        ):
            raise ValueError("content_hash must be lowercase hexadecimal SHA-256")
        if not isinstance(self.blocks, tuple) or any(
            not isinstance(block, ObservationBlock) for block in self.blocks
        ):
            raise ValueError("blocks must be a tuple of validated ObservationBlock values")
        source_hash = self.source_content_hash or self.content_hash
        if re.fullmatch(r"[0-9a-f]{64}", source_hash) is None:
            raise ValueError("source_content_hash must be lowercase hexadecimal SHA-256")
        object.__setattr__(self, "source_content_hash", source_hash)
        object.__setattr__(self, "content_hash", canonical_observation_hash(self.blocks))


@dataclass(frozen=True, slots=True)
class UserIntent:
    """Boundary view of the PRD's explicit constraints and ranking preferences."""

    max_price_minor: int | None
    currency: str
    required_specs: Mapping[str, str]
    allowed_merchants: tuple[str, ...] | None
    weights: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class ProductFact:
    candidate_id: str
    name: str
    price_minor: int
    currency: str
    seller_id: str
    spec: Mapping[str, str | int | bool]
    sku: str | None = None
    gtin: str | None = None
    source_span: tuple[int, int] | None = None
    shipping_minor: int | None = None
    additional_charges_minor: int | None = None

    def __post_init__(self) -> None:
        for field_name in ("candidate_id", "name", "seller_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be non-empty text")
        if type(self.price_minor) is not int or self.price_minor < 0:
            raise ValueError("price_minor must be a non-negative integer")
        if not isinstance(self.currency, str) or re.fullmatch(r"[A-Z]{3}", self.currency) is None:
            raise ValueError("currency must be a three-letter uppercase code")
        for field_name in ("sku", "gtin"):
            value = getattr(self, field_name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{field_name} must be non-empty text when provided")
        for field_name in ("shipping_minor", "additional_charges_minor"):
            value = getattr(self, field_name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{field_name} must be a non-negative integer when provided")
        if not isinstance(self.spec, Mapping):
            raise ValueError("spec must be a mapping")
        copied_spec = dict(self.spec)
        if any(
            not isinstance(key, str) or not key.strip() or type(value) not in (str, int, bool)
            for key, value in copied_spec.items()
        ):
            raise ValueError("spec values must use non-empty keys and strict scalar types")
        object.__setattr__(self, "spec", MappingProxyType(copied_spec))
        if self.source_span is not None and (
            not isinstance(self.source_span, tuple)
            or len(self.source_span) != 2
            or any(type(offset) is not int or offset < 0 for offset in self.source_span)
            or self.source_span[1] < self.source_span[0]
        ):
            raise ValueError("source_span must contain ordered non-negative integer offsets")


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    run_id: str
    candidate_ids: tuple[str, ...]
    facts: tuple[ProductFact, ...]


@dataclass(frozen=True, slots=True)
class RankingResult:
    run_id: str
    winner_candidate_id: str | None
    ranked_candidate_ids: tuple[str, ...]


class Extractor(Protocol):
    def extract(
        self,
        observations: tuple[CandidateObservation, ...],
        intent: UserIntent,
        *,
        run_id: str,
        timeout_seconds: float,
    ) -> ExtractionResult: ...


class Ranker(Protocol):
    def rank(
        self,
        extraction: ExtractionResult,
        intent: UserIntent,
        *,
        run_id: str,
        timeout_seconds: float,
    ) -> RankingResult: ...
