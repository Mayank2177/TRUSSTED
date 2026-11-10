"""Stage 3: deterministic ranking. No LLM, no free text: only typed facts and the user's intent.

Hard constraints disqualify. Weights rank only the survivors. Output is a pure function of its
inputs and independent of input order.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_EVEN, Decimal

from ..config import RankConfig, VerifyConfig
from ..errors import RankingError, ValidationError
from ..models.facts import FactVerification, ProductFact
from ..models.intent import UserIntent
from ..models.money import Money
from ..models.results import (
    DisqualifiedCandidate,
    FlagCode,
    RankedCandidate,
    RankResult,
    Violation,
    ViolationCode,
)
from ..models.units import parse_spec_value, spec_matches
from ..verify.keys import SpecKeyResolver

V = ViolationCode


def _name_matches(value: str, targets: frozenset[str]) -> bool:
    v = " ".join(value.casefold().split())
    return any(v == t or v.startswith(t + " ") for t in targets)


def _merchant_matches(merchant_id: str, targets: frozenset[str]) -> bool:
    return any(merchant_id == t or merchant_id.endswith("." + t) for t in targets)


def total_cost(fact: ProductFact, quantity: int) -> Money:
    total = fact.price * quantity
    if fact.shipping is not None:
        total = total + fact.shipping
    if fact.additional_charges is not None:
        total = total + fact.additional_charges
    return total


def _evaluate(
    fact: ProductFact, intent: UserIntent, ver: FactVerification | None, cfg: RankConfig,
    keys: SpecKeyResolver,
) -> tuple[list[Violation], list[FlagCode]]:
    violations: list[Violation] = []
    flags: list[FlagCode] = []

    def unknown(field: str, violation: ViolationCode, flag: FlagCode, detail: str) -> None:
        if cfg.policy_for(field) == "violation":
            violations.append(Violation(violation, detail))
        else:
            flags.append(flag)

    if fact.price.currency != intent.currency:
        violations.append(Violation(V.CURRENCY_MISMATCH,
                                    f"{fact.price.currency} != {intent.currency}"))
    else:
        if fact.shipping is None:
            unknown("shipping", V.SHIPPING_UNKNOWN, FlagCode.COST_LOWER_BOUND, "shipping not stated")
            if cfg.policy_for("shipping") != "violation":
                pass  # COST_LOWER_BOUND already appended
        total = total_cost(fact, intent.quantity)
        if intent.max_total is not None and total > intent.max_total:
            violations.append(Violation(V.OVER_BUDGET, f"{total} > {intent.max_total}"))

    if intent.allowed_brands:
        if not fact.brand:
            violations.append(Violation(V.BRAND_UNKNOWN, "brand not stated"))
        elif not _name_matches(fact.brand, intent.allowed_brands):
            violations.append(Violation(V.BRAND_NOT_ALLOWED, fact.brand))
    if fact.brand and intent.blocked_brands and _name_matches(fact.brand, intent.blocked_brands):
        violations.append(Violation(V.BRAND_BLOCKED, fact.brand))
    if intent.allowed_merchants and not _merchant_matches(fact.merchant_id, intent.allowed_merchants):
        violations.append(Violation(V.MERCHANT_NOT_ALLOWED, fact.merchant_id))
    if intent.blocked_merchants and _merchant_matches(fact.merchant_id, intent.blocked_merchants):
        violations.append(Violation(V.MERCHANT_BLOCKED, fact.merchant_id))

    fact_specs = keys.index(fact.specs)
    for c in intent.spec_constraints:
        key = keys.canonical(c.key)
        if key not in fact_specs:
            violations.append(Violation(V.SPEC_MISSING, c.key))
            continue
        try:
            outcome = spec_matches(c.op, parse_spec_value(fact_specs[key]),
                                   tuple(parse_spec_value(v) for v in c.values))
        except ValidationError:
            outcome = None
        detail = f"{c.key} {c.op} {list(c.values)} (page: {fact_specs[key]!r})"
        if outcome is None:
            violations.append(Violation(V.SPEC_UNCOMPARABLE, detail))
        elif not outcome:
            violations.append(Violation(V.SPEC_MISMATCH, detail))

    if not intent.allow_recurring:
        if fact.is_recurring:
            violations.append(Violation(V.RECURRING_CHARGE, "page indicates a recurring charge"))
        elif fact.is_recurring is None:
            unknown("recurring", V.RECURRING_UNKNOWN, FlagCode.RECURRING_UNKNOWN,
                    "recurring status not stated")

    if intent.max_delivery_days is not None:
        if fact.delivery_days is None:
            unknown("delivery", V.DELIVERY_UNKNOWN, FlagCode.DELIVERY_UNKNOWN, "delivery not stated")
        elif fact.delivery_days > intent.max_delivery_days:
            violations.append(Violation(V.DELIVERY_TOO_SLOW,
                                        f"{fact.delivery_days}d > {intent.max_delivery_days}d"))

    if not intent.allow_used:
        if fact.condition in ("used", "refurbished"):
            violations.append(Violation(V.CONDITION_NOT_ALLOWED, fact.condition))
        elif fact.condition == "unknown":
            unknown("condition", V.CONDITION_UNKNOWN, FlagCode.CONDITION_UNKNOWN,
                    "condition not stated")

    if ver is not None and ver.conflicts:
        if cfg.exclude_high_conflicts and ver.has_high_conflict:
            fields = ", ".join(sorted({c.field for c in ver.conflicts if c.severity == "high"}))
            violations.append(Violation(V.FACT_CONFLICT_HIGH, fields))
        else:
            flags.append(FlagCode.CONFLICT_PRESENT)
    if ver is None or (ver.status != "verified" and not ver.conflicts):
        flags.append(FlagCode.NO_INDEPENDENT_REFERENCE)
    if fact.warnings:
        flags.append(FlagCode.EXTRACTION_WARNINGS)
    return violations, sorted(set(flags), key=lambda f: f.value)  # type: ignore[return-value]


def _ratio_to_best(
    values: Sequence[Decimal | None], offset: Decimal, missing: Decimal
) -> list[Decimal]:
    """Lower is better. Score = (best + offset) / (value + offset), in (0, 1]; None -> missing.

    Ratio scoring keeps near-equal values near-equal (a 1-cent price gap is a ~0 score gap),
    unlike min-max scaling, and has no degenerate all-equal case.
    """
    present = [v for v in values if v is not None]
    if not present:
        return [missing] * len(values)
    best = min(present)
    return [missing if v is None else (best + offset) / (v + offset) for v in values]


def rank_candidates(
    intent: UserIntent,
    facts: Sequence[ProductFact],
    verifications: Sequence[FactVerification],
    config: RankConfig,
    verify_config: VerifyConfig,
) -> RankResult:
    ids = [f.fact_id for f in facts]
    if len(ids) != len(set(ids)):
        raise RankingError("duplicate fact_id in ranking input")
    keys = SpecKeyResolver(verify_config.spec_aliases)
    ver_by_id: Mapping[str, FactVerification] = {v.fact_id: v for v in verifications}

    eligible: list[tuple[ProductFact, Money, list[FlagCode]]] = []
    disqualified: list[DisqualifiedCandidate] = []
    for fact in facts:
        violations, flags = _evaluate(fact, intent, ver_by_id.get(fact.fact_id), config, keys)
        if violations:
            disqualified.append(DisqualifiedCandidate(fact, tuple(violations)))
        else:
            eligible.append((fact, total_cost(fact, intent.quantity), flags))
    disqualified.sort(key=lambda d: (d.fact.merchant_id, d.fact.fact_id))

    if not eligible:
        return RankResult((), tuple(disqualified), None, None)

    w = intent.weights
    wsum = w.price + w.delivery + w.rating
    miss = config.missing_component_score
    price_c = _ratio_to_best([Decimal(t.amount_minor) for _, t, _ in eligible], Decimal(0), miss)
    deliv_c = _ratio_to_best([
        None if f.delivery_days is None else Decimal(f.delivery_days) for f, _, _ in eligible
    ], Decimal(1), miss)
    quantum = Decimal(1).scaleb(-config.score_places)
    scored: list[tuple[Decimal, ProductFact, Money, list[FlagCode]]] = []
    for i, (fact, total, flags) in enumerate(eligible):
        rating_c = miss if fact.rating is None else fact.rating / Decimal(5)
        raw = (w.price * price_c[i] + w.delivery * deliv_c[i] + w.rating * rating_c) / wsum
        scored.append((raw.quantize(quantum, rounding=ROUND_HALF_EVEN), fact, total, flags))
    scored.sort(key=lambda s: (-s[0], s[2].amount_minor, s[1].merchant_id, s[1].fact_id))

    ranked = tuple(
        RankedCandidate(rank=i + 1, fact=f, total_cost=t, score=sc, flags=tuple(fl))
        for i, (sc, f, t, fl) in enumerate(scored)
    )
    margin = ranked[0].score - ranked[1].score if len(ranked) > 1 else None
    return RankResult(ranked, tuple(disqualified), ranked[0].fact.fact_id, margin)
