from __future__ import annotations

from types import SimpleNamespace

import pytest

from warrant.integrity.mayank_adapter import adapt_mayank_selection


def mayank_selection():
    """Mirror the ProductFact/RankResult/SelectionResult shapes in Mayank's archive."""
    first = SimpleNamespace(
        fact_id="obs-a-fact-0",
        observation_id="obs-a",
        merchant_id="marketplace.example",
        name="Fictional SSD",
        price=SimpleNamespace(amount_minor=12_500, currency="USD"),
        brand="Fictional",
        sku="SKU-A",
        gtin=None,
        shipping=SimpleNamespace(amount_minor=0, currency="USD"),
        additional_charges=None,
        delivery_days=3,
        rating=None,
        condition="new",
        specs={"capacity": "1 TB"},
    )
    second = SimpleNamespace(
        fact_id="obs-b-fact-0",
        observation_id="obs-b",
        merchant_id="store.example",
        name="Fictional SSD 1TB",
        price=SimpleNamespace(amount_minor=13_000, currency="USD"),
        brand="Fictional",
        sku="SKU-B",
        gtin="123",
        shipping=None,
        additional_charges=None,
        delivery_days=None,
        rating=None,
        condition="unknown",
        specs={},
    )
    return SimpleNamespace(
        facts=(first, second),
        ranking=SimpleNamespace(
            ranked=(SimpleNamespace(fact=second), SimpleNamespace(fact=first)),
            winner_fact_id=second.fact_id,
        ),
        stage_errors=(SimpleNamespace(stage="verify", ref="-", message="private detail"),),
        verifications=(),
    )


def test_adapts_mayank_facts_and_rank_order_using_explicit_identity_maps() -> None:
    result = adapt_mayank_selection(
        mayank_selection(),
        run_id="parent-run",
        candidate_id_by_fact_id={"obs-a-fact-0": "candidate-a", "obs-b-fact-0": "candidate-b"},
        seller_id_by_fact_id={
            "obs-a-fact-0": "seller-authoritative-a",
            "obs-b-fact-0": "seller-authoritative-b",
        },
    )

    assert result.extraction.run_id == "parent-run"
    assert result.extraction.candidate_ids == ("candidate-a", "candidate-b")
    assert result.extraction.facts[0].candidate_id == "candidate-a"
    assert result.extraction.facts[0].seller_id == "seller-authoritative-a"
    assert result.extraction.facts[0].shipping_minor == 0
    assert result.extraction.facts[0].source_span is None
    assert result.ranking.winner_candidate_id == "candidate-b"
    assert result.ranking.ranked_candidate_ids == ("candidate-b", "candidate-a")
    assert result.upstream_failures[0].stage == "verify"
    assert result.upstream_failures[0].code == "MAYANK_STAGE_ERROR"
    assert "private detail" not in result.upstream_failures[0].code
    assert result.no_reference_by_candidate_id == {"candidate-a": True, "candidate-b": True}


def test_maps_mayank_conflict_severity_and_reference_availability() -> None:
    selection = mayank_selection()
    selection.verifications = (
        SimpleNamespace(
            fact_id="obs-b-fact-0",
            status="conflict",
            independent_sources=("reference-source",),
            conflicts=(
                SimpleNamespace(
                    fact_id="obs-b-fact-0",
                    field="price",
                    severity="high",
                ),
            ),
        ),
    )
    result = adapt_mayank_selection(
        selection,
        run_id="parent-run",
        candidate_id_by_fact_id={"obs-a-fact-0": "candidate-a", "obs-b-fact-0": "candidate-b"},
        seller_id_by_fact_id={"obs-a-fact-0": "seller-a", "obs-b-fact-0": "seller-b"},
    )
    assert result.conflicts[0].field == "price"
    assert result.conflicts[0].severity.value == "high"
    assert result.conflicts[0].fact_id == "candidate-b"
    assert result.no_reference_by_candidate_id["candidate-b"] is False


def test_does_not_infer_candidate_or_actual_seller_from_mayank_ids_or_hostnames() -> None:
    selection = mayank_selection()
    with pytest.raises(ValueError, match="candidate mapping"):
        adapt_mayank_selection(
            selection,
            run_id="parent-run",
            candidate_id_by_fact_id={},
            seller_id_by_fact_id={},
        )

    with pytest.raises(ValueError, match="verified seller IDs"):
        adapt_mayank_selection(
            selection,
            run_id="parent-run",
            candidate_id_by_fact_id={"obs-a-fact-0": "candidate-a", "obs-b-fact-0": "candidate-b"},
            seller_id_by_fact_id={
                "obs-a-fact-0": "marketplace.example",
                "obs-b-fact-0": "store.example",
            },
        )


def test_rejects_a_winner_that_is_not_the_first_ranked_fact() -> None:
    selection = mayank_selection()
    selection.ranking.winner_fact_id = "obs-a-fact-0"
    with pytest.raises(ValueError, match="first ranked fact"):
        adapt_mayank_selection(
            selection,
            run_id="parent-run",
            candidate_id_by_fact_id={"obs-a-fact-0": "candidate-a", "obs-b-fact-0": "candidate-b"},
            seller_id_by_fact_id={"obs-a-fact-0": "seller-a", "obs-b-fact-0": "seller-b"},
        )
