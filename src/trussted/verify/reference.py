"""Independent reference data (e.g. an attested merchant feed or a catalog)."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any, Protocol

from ..errors import ConfigError, ValidationError
from ..models.facts import ProductFact
from ..models.ids import normalize_gtin
from ..models.money import Money, parse_amount


@dataclass(frozen=True, slots=True)
class ReferenceRecord:
    gtin: str | None = None
    merchant_id: str | None = None
    sku: str | None = None
    brand: str | None = None
    price: Money | None = None
    specs: Mapping[str, str] = MappingProxyType({})
    is_recurring: bool | None = None

    def __post_init__(self) -> None:
        if self.gtin is not None and normalize_gtin(self.gtin) is None:
            raise ValidationError(f"invalid GTIN in reference record: {self.gtin!r}")
        if not self.gtin and not (self.merchant_id and self.sku):
            raise ValidationError("reference record needs a gtin or (merchant_id and sku)")
        if self.merchant_id:
            object.__setattr__(self, "merchant_id", self.merchant_id.strip().casefold())
        object.__setattr__(self, "specs", MappingProxyType(dict(self.specs)))


class ReferenceSource(Protocol):
    name: str

    def lookup(self, fact: ProductFact) -> ReferenceRecord | None: ...


class InMemoryReferenceSource:
    """Lookup by GTIN first, then by (merchant_id, sku)."""

    def __init__(self, name: str, records: Iterable[ReferenceRecord]) -> None:
        if not name.strip():
            raise ConfigError("reference source needs a name")
        self.name = name
        self._by_gtin: dict[str, ReferenceRecord] = {}
        self._by_sku: dict[tuple[str, str], ReferenceRecord] = {}
        for rec in records:
            if rec.gtin:
                self._put(self._by_gtin, rec.gtin, rec)
            if rec.merchant_id and rec.sku:
                self._put(self._by_sku, (rec.merchant_id, rec.sku.casefold()), rec)

    @staticmethod
    def _put(index: dict[Any, ReferenceRecord], key: Any, rec: ReferenceRecord) -> None:
        if key in index and index[key] != rec:
            raise ConfigError(f"conflicting duplicate reference records for {key!r}")
        index[key] = rec

    def lookup(self, fact: ProductFact) -> ReferenceRecord | None:
        if fact.gtin and fact.gtin in self._by_gtin:
            return self._by_gtin[fact.gtin]
        if fact.sku:
            return self._by_sku.get((fact.merchant_id, fact.sku.casefold()))
        return None

    @classmethod
    def from_json_file(cls, path: str | Path, name: str) -> InMemoryReferenceSource:
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"cannot read reference file {path}: {exc}") from exc
        if not isinstance(raw, list):
            raise ConfigError("reference file must contain a JSON list")
        records = []
        for i, item in enumerate(raw):
            try:
                price = None
                if item.get("price") is not None:
                    dec: Decimal = parse_amount(str(item["price"]))
                    price = Money.from_decimal(dec, str(item["currency"]).upper())
                records.append(ReferenceRecord(
                    gtin=item.get("gtin"), merchant_id=item.get("merchant_id"),
                    sku=item.get("sku"), brand=item.get("brand"), price=price,
                    specs={str(k): str(v) for k, v in (item.get("specs") or {}).items()},
                    is_recurring=item.get("is_recurring"),
                ))
            except (ValidationError, KeyError, AttributeError, TypeError) as exc:
                raise ConfigError(f"invalid reference record #{i}: {exc}") from exc
        return cls(name, records)
