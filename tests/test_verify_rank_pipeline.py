import itertools
import json
import unittest
from decimal import Decimal

from trussted.config import RankConfig, Settings, VerifyConfig
from trussted.llm.stub import CassetteClient, StubClient
from trussted.models import Money, ScoringWeights, ViolationCode as V
from trussted.rank import rank_candidates
from trussted.verify import InMemoryReferenceSource, ReferenceRecord

from .helpers import SAMSUNG_GTIN, intent, page, pipeline, product

SSD_BODY = "<h1>Samsung 990 SSD</h1><p>Capacity 1TB</p><p>Price $89.99</p><p>Shipping $5.00</p>"
SSD = product("Samsung 990 SSD", "89.99", "Price $89.99", brand="Samsung", gtin=SAMSUNG_GTIN,
              shipping_price="5.00", is_recurring=False, condition="new",
              specs={"Capacity": "1TB"})


class EndToEndTests(unittest.TestCase):
    def test_cartlock_style_scenario(self):
        """Wrong brand at $149 and a subscription add-on are eliminated; the right SSD wins."""
        bodies = {
            "https://good.example/ssd": SSD_BODY,
            "https://brandx.example/ssd": "<p>BrandX 1TB SSD</p><p>Price $149.00</p>",
            "https://sub.example/ssd": "<p>Samsung 990 SSD 1TB</p><p>Price $59.00 with Plus subscription</p>",
        }
        responses = {
            "good": {"products": [SSD]},
            "brandx": {"products": [product("BrandX 1TB SSD", "149.00", "Price $149.00",
                                            brand="BrandX", specs={"Capacity": "1TB"},
                                            is_recurring=False, condition="new")]},
            "sub": {"products": [product("Samsung 990 SSD 1TB", "59.00", "Price $59.00",
                                         brand="Samsung", specs={"Capacity": "1TB"},
                                         is_recurring=True, condition="new")]},
        }
        def route(req):
            u = req.user.lower()
            return responses["sub"] if "plus subscription" in u else \
                   responses["brandx"] if "brandx" in u else responses["good"]
        pipe, _ = pipeline(route)
        res = pipe.run(intent(), [page(u, b) for u, b in bodies.items()])
        self.assertFalse(res.has_errors)
        self.assertEqual(res.winner.merchant_id, "good.example")
        codes = {d.fact.merchant_id: {v.code for v in d.violations} for d in res.ranking.disqualified}
        self.assertIn(V.BRAND_NOT_ALLOWED, codes["brandx.example"])
        self.assertIn(V.OVER_BUDGET, codes["brandx.example"])
        self.assertIn(V.RECURRING_CHARGE, codes["sub.example"])
        self.assertEqual(str(res.ranking.ranked[0].total_cost), "94.99 USD")

    def test_spec_swap_detected_from_page_structured_data(self):
        """Prose says 1TB, structured data says 128GB, same price -> high conflict -> excluded."""
        ld = {"@type": "Product", "name": "Samsung 990 SSD", "gtin13": SAMSUNG_GTIN,
              "offers": {"price": "89.99", "priceCurrency": "USD"},
              "additionalProperty": [{"name": "Storage", "value": "128GB"}]}
        pipe, _ = pipeline([{"products": [SSD]}])
        res = pipe.run(intent(), [page("https://shady.example/ssd", SSD_BODY, ld)])
        v = res.verifications[0]
        self.assertEqual(v.status, "conflict")
        self.assertEqual(v.conflicts[0].field, "spec:capacity")  # alias storage -> capacity
        self.assertIsNone(res.ranking.winner_fact_id)
        self.assertEqual(res.ranking.disqualified[0].violations[0].code, V.FACT_CONFLICT_HIGH)

    def test_independent_reference_price_conflict_and_verified(self):
        ref = InMemoryReferenceSource("catalog", [ReferenceRecord(
            gtin=SAMSUNG_GTIN, price=Money.from_decimal(Decimal("129.99"), "USD"),
            brand="Samsung", specs={"capacity": "1000 GB"}, is_recurring=False)])
        pipe, _ = pipeline([{"products": [SSD]}], [ref])
        res = pipe.run(intent(), [page("https://s.example/ssd", SSD_BODY)])
        self.assertEqual([c.kind for c in res.verifications[0].conflicts], ["price"])

        ok = InMemoryReferenceSource("catalog", [ReferenceRecord(
            gtin=SAMSUNG_GTIN, price=Money.from_decimal(Decimal("89.99"), "USD"),
            brand="samsung", specs={"capacity": "1000 GB"})])
        pipe, _ = pipeline([{"products": [SSD]}], [ok])
        res = pipe.run(intent(), [page("https://s.example/ssd", SSD_BODY)])
        self.assertEqual(res.verifications[0].status, "verified")
        self.assertEqual(res.winner.fact_id, res.facts[0].fact_id)

    def test_partial_failure_is_isolated_and_reported(self):
        from trussted.errors import LLMError
        pipe, _ = pipeline([LLMError("down"), {"products": [SSD]}])
        res = pipe.run(intent(), [page("https://a.example/x", "<p>a</p>"), page("https://b.example/ssd", SSD_BODY)])
        self.assertTrue(res.has_errors)
        self.assertEqual(res.stage_errors[0].stage, "extract")
        self.assertIsNotNone(res.winner)

    def test_input_validation_and_dedupe(self):
        from trussted.errors import ValidationError
        pipe, _ = pipeline([{"products": [SSD]}])
        with self.assertRaises(ValidationError):
            pipe.run(intent(), [])
        pg = page("https://s.example/ssd", SSD_BODY)
        pipe, _ = pipeline([{"products": [SSD]}, {"products": [SSD]}])
        res = pipe.run(intent(), [pg, pg])
        self.assertEqual(len(res.facts), 1)
        self.assertTrue(any(w.startswith("duplicate_page") for w in res.warnings))

    def test_failing_reference_source_is_reported_not_swallowed(self):
        class Boom:
            name = "boom"
            def lookup(self, fact): raise OSError("disk")
        pipe, _ = pipeline([{"products": [SSD]}], [Boom()])
        res = pipe.run(intent(), [page("https://s.example/ssd", SSD_BODY)])
        self.assertEqual(res.stage_errors[0].stage, "verify")
        self.assertEqual(res.verifications[0].status, "no_reference")


class RankTests(unittest.TestCase):
    def _two(self):
        a = product("Samsung 990 SSD", "80.00", "Price $80.00", brand="Samsung", specs={"capacity": "1TB"},
                    shipping_price="9.00", is_recurring=False, condition="new", delivery_days=7, rating="4")
        b = product("Samsung 980 SSD", "85.00", "Price $85.00", brand="Samsung", specs={"capacity": "1TB"},
                    shipping_price="0", is_recurring=False, condition="new", delivery_days=2, rating="5")
        from trussted.extract import ProductExtractor
        from trussted.config import ExtractionConfig, SanitizeConfig
        ex = ProductExtractor(StubClient([{"products": [a, b]}]), ExtractionConfig(), SanitizeConfig())
        return ex.extract(page("https://s.example/p", "<p>Price $80.00</p><p>Price $85.00</p>")).facts

    def test_weights_change_winner_and_order_independence(self):
        facts = self._two()
        rc, vc = RankConfig(), VerifyConfig()
        by_price = rank_candidates(intent(), facts, (), rc, vc)
        cheapest = min(facts, key=lambda f: f.price.amount_minor + f.shipping.amount_minor)
        self.assertEqual(by_price.winner_fact_id, cheapest.fact_id)  # total cost 89 vs 85 -> 980 wins
        fast = rank_candidates(intent(weights=ScoringWeights(Decimal(0), Decimal(1), Decimal(0))), facts, (), rc, vc)
        self.assertEqual(fast.ranked[0].fact.delivery_days, 2)
        winners = {rank_candidates(intent(), list(p), (), rc, vc).winner_fact_id
                   for p in itertools.permutations(facts)}
        self.assertEqual(len(winners), 1)

    def test_tie_break_is_stable(self):
        facts = self._two()
        tie = intent(weights=ScoringWeights(Decimal(0), Decimal(0), Decimal(1)))
        r1 = rank_candidates(tie, facts, (), RankConfig(), VerifyConfig())
        r2 = rank_candidates(tie, list(reversed(facts)), (), RankConfig(), VerifyConfig())
        self.assertEqual([c.fact.fact_id for c in r1.ranked], [c.fact.fact_id for c in r2.ranked])

    def test_unknown_policy_and_quantity_and_currency(self):
        facts = self._two()
        strict = RankConfig(unknown_policy={"recurring": "violation", "shipping": "violation"})
        r = rank_candidates(intent(quantity=2, max_total=Money.from_decimal(Decimal("170"), "USD")),
                            facts, (), strict, VerifyConfig())
        self.assertEqual(len(r.ranked) + len(r.disqualified), 2)
        self.assertTrue(all(d.violations[0].code == V.OVER_BUDGET for d in r.disqualified))
        eur = intent(currency="EUR", max_total=Money.from_decimal(Decimal("100"), "EUR"))
        r = rank_candidates(eur, facts, (), RankConfig(), VerifyConfig())
        self.assertIsNone(r.winner_fact_id)
        self.assertEqual(r.disqualified[0].violations[0].code, V.CURRENCY_MISMATCH)

    def test_duplicate_ids_rejected(self):
        from trussted.errors import RankingError
        f = self._two()
        with self.assertRaises(RankingError):
            rank_candidates(intent(), [f[0], f[0]], (), RankConfig(), VerifyConfig())

    def test_no_candidates(self):
        r = rank_candidates(intent(), [], (), RankConfig(), VerifyConfig())
        self.assertEqual((r.ranked, r.winner_fact_id, r.winner_margin), ((), None, None))


class CassetteTests(unittest.TestCase):
    def test_record_then_replay(self):
        import os, tempfile
        path = os.path.join(tempfile.mkdtemp(), "c.json")
        live = StubClient([{"products": []}])
        from trussted.llm.base import LLMRequest
        req = LLMRequest("s", "u", {"type": "object"}, 0, 5.0)
        CassetteClient(path, record_with=live).complete_json(req)
        replay = CassetteClient(path)
        self.assertEqual(replay.complete_json(req).data, {"products": []})
        from trussted.errors import ConfigError, LLMResponseError
        with self.assertRaises(LLMResponseError):
            replay.complete_json(LLMRequest("s", "other", {"type": "object"}, 0, 5.0))
        with self.assertRaises(ConfigError):
            CassetteClient(path + ".missing")


if __name__ == "__main__":
    unittest.main()
