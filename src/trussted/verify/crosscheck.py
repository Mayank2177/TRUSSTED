"""Stage 2: compare extracted facts with the page's own structured data and with independent
reference sources. 'verified' requires an independent reference; the page agreeing with itself
is recorded but does not count as independent."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from ..config import VerifyConfig
from ..errors import ValidationError, VerificationError
from ..models.facts import FactConflict, FactVerification, Observation, ProductFact, StructuredProduct
from ..models.money import Money
from ..models.results import StageError
from ..models.units import parse_spec_value, spec_equal
from .keys import SpecKeyResolver
from .reference import ReferenceSource

logger = logging.getLogger(__name__)
PAGE_SOURCE = "page_structured_data"


@dataclass(frozen=True, slots=True)
class _View:
    """Source-agnostic comparable fields."""

    price: Money | None
    brand: str | None
    specs: Mapping[str, str]
    is_recurring: bool | None


def _view_from_structured(sp: StructuredProduct) -> _View:
    price = None
    if sp.price is not None and sp.currency:
        try:
            price = Money.from_decimal(sp.price, sp.currency)
        except ValidationError:
            price = None
    return _View(price, sp.brand, sp.specs, None)


def _norm(s: str) -> str:
    return " ".join(s.casefold().split())


def _structured_match(fact: ProductFact, candidates: Sequence[StructuredProduct]) -> StructuredProduct | None:
    def by(pred) -> list[StructuredProduct]:  # type: ignore[no-untyped-def]
        return [c for c in candidates if pred(c)]

    for pred in (
        lambda c: bool(fact.gtin and c.gtin and fact.gtin == c.gtin),
        lambda c: bool(fact.sku and c.sku and _norm(fact.sku) == _norm(c.sku)),
        lambda c: bool(c.name and _norm(c.name) == _norm(fact.name)),
    ):
        hits = by(pred)
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            return None  # ambiguous: do not guess
    return None


class CrossChecker:
    def __init__(self, sources: Sequence[ReferenceSource], config: VerifyConfig) -> None:
        self._sources = tuple(sources)
        self._cfg = config
        self._keys = SpecKeyResolver(config.spec_aliases)

    def verify(
        self, facts: Sequence[ProductFact], observations: Sequence[Observation]
    ) -> tuple[tuple[FactVerification, ...], tuple[StageError, ...]]:
        by_obs = {o.observation_id: o for o in observations}
        results: list[FactVerification] = []
        errors: list[StageError] = []
        for fact in facts:
            obs = by_obs.get(fact.observation_id)
            if obs is None:
                raise VerificationError(f"fact {fact.fact_id} references unknown observation")
            conflicts: list[FactConflict] = []
            consulted: list[str] = []
            independent: list[str] = []

            match = _structured_match(fact, obs.structured)
            if match is not None:
                consulted.append(PAGE_SOURCE)
                conflicts += self._compare(fact, _view_from_structured(match), PAGE_SOURCE)

            for source in self._sources:
                try:
                    record = source.lookup(fact)
                except Exception as exc:  # noqa: BLE001 - third-party plugin boundary
                    logger.warning("reference source %s failed: %s", source.name, type(exc).__name__)
                    errors.append(StageError("verify", fact.fact_id,
                                             f"{source.name}: {type(exc).__name__}: {exc}"))
                    continue
                if record is None:
                    continue
                consulted.append(source.name)
                independent.append(source.name)
                conflicts += self._compare(
                    fact, _View(record.price, record.brand, record.specs, record.is_recurring),
                    source.name,
                )

            status = "conflict" if conflicts else ("verified" if independent else "no_reference")
            results.append(FactVerification(
                fact.fact_id, status, tuple(conflicts), tuple(consulted), tuple(independent)
            ))
        return tuple(results), tuple(errors)

    # -- comparison -------------------------------------------------------------------------
    def _conflict(self, fact: ProductFact, kind: str, field: str, ext: str, ref: str,
                  source: str) -> FactConflict:
        return FactConflict(fact.fact_id, kind, field, ext, ref, self._cfg.severity(kind), source)

    def _compare(self, fact: ProductFact, ref: _View, source: str) -> list[FactConflict]:
        out: list[FactConflict] = []
        if ref.price is not None:
            if ref.price.currency != fact.price.currency:
                out.append(self._conflict(fact, "currency", "price.currency",
                                          fact.price.currency, ref.price.currency, source))
            else:
                allowed = max(
                    Decimal(self._cfg.price_tolerance_minor),
                    Decimal(ref.price.amount_minor) * self._cfg.price_tolerance_pct / 100,
                )
                if abs(fact.price.amount_minor - ref.price.amount_minor) > allowed:
                    out.append(self._conflict(fact, "price", "price", str(fact.price),
                                              str(ref.price), source))
        if fact.brand and ref.brand and _norm(fact.brand) != _norm(ref.brand):
            out.append(self._conflict(fact, "brand", "brand", fact.brand, ref.brand, source))
        if fact.is_recurring is not None and ref.is_recurring is not None \
                and fact.is_recurring != ref.is_recurring:
            out.append(self._conflict(fact, "recurring", "is_recurring", str(fact.is_recurring),
                                      str(ref.is_recurring), source))
        fact_specs = self._keys.index(fact.specs)
        for key, ref_value in self._keys.index(ref.specs).items():
            if key not in fact_specs:
                continue
            try:
                same = spec_equal(parse_spec_value(fact_specs[key]), parse_spec_value(ref_value))
            except ValidationError:
                same = False
            if not same:
                out.append(self._conflict(fact, "spec", f"spec:{key}", fact_specs[key],
                                          ref_value, source))
        return out
