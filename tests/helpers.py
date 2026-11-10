from __future__ import annotations

import json
from decimal import Decimal

from trussted.config import Settings
from trussted.llm.stub import StubClient
from trussted.models import Money, PageInput, ScoringWeights, SpecConstraint, UserIntent
from trussted.pipeline import SelectionPipeline
from trussted.verify import InMemoryReferenceSource, ReferenceRecord

SAMSUNG_GTIN = "4006381333931"  # valid EAN-13


def page(url: str, body: str, jsonld: dict | None = None) -> PageInput:
    ld = f'<script type="application/ld+json">{json.dumps(jsonld)}</script>' if jsonld else ""
    return PageInput(url, f"<html><head>{ld}</head><body>{body}</body></html>")


def product(name: str, price: str, evidence: str, **kw) -> dict:
    base = {"name": name, "price": price, "currency": "USD", "evidence": evidence}
    base.update(kw)
    return base


def intent(**kw) -> UserIntent:
    base = dict(description="Samsung 1TB SSD", currency="USD",
                max_total=Money.from_decimal(Decimal("100"), "USD"),
                allowed_brands=frozenset({"samsung"}),
                spec_constraints=(SpecConstraint("capacity", "eq", ("1TB",)),))
    base.update(kw)
    return UserIntent(**base)


def pipeline(responses, references=(), settings: Settings | None = None):
    llm = StubClient(responses)
    return SelectionPipeline.build(llm, references, settings), llm
