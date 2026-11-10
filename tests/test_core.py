import unittest
from decimal import Decimal

from trussted.config import RankConfig, Settings
from trussted.errors import ConfigError, ValidationError
from trussted.models import Money, ScoringWeights, SpecConstraint, UserIntent, parse_amount
from trussted.models.ids import merchant_id_from_url, normalize_gtin
from trussted.models.units import parse_spec_value, spec_matches


class MoneyTests(unittest.TestCase):
    def test_exact_and_exponents(self):
        self.assertEqual(Money.from_decimal(Decimal("99.99"), "USD").amount_minor, 9999)
        self.assertEqual(Money.from_decimal(Decimal("500"), "JPY").amount_minor, 500)
        self.assertEqual(Money.from_decimal(Decimal("1.234"), "KWD").amount_minor, 1234)
        self.assertEqual(str(Money(9999, "USD")), "99.99 USD")

    def test_rejects_excess_precision_and_bad_inputs(self):
        with self.assertRaises(ValidationError):
            Money.from_decimal(Decimal("1.999"), "USD")
        with self.assertRaises(ValidationError):
            Money.from_decimal(Decimal("NaN"), "USD")
        with self.assertRaises(ValidationError):
            Money(True, "USD")
        with self.assertRaises(ValidationError):
            Money(1, "usd")

    def test_currency_mismatch_and_ordering(self):
        with self.assertRaises(ValidationError):
            Money(1, "USD") + Money(1, "EUR")
        with self.assertRaises(ValidationError):
            Money(1, "USD") < Money(2, "EUR")
        self.assertTrue(Money(1, "USD") < Money(2, "USD"))
        self.assertEqual(Money(150, "USD") * 3, Money(450, "USD"))

    def test_parse_amount(self):
        self.assertEqual(parse_amount("1,299.99"), Decimal("1299.99"))
        self.assertEqual(parse_amount(" 99 "), Decimal("99"))
        for bad in ("1.299,99", "1e5", "$5", "", "-3", "1,29", "9" * 30):
            with self.assertRaises(ValidationError, msg=bad):
                parse_amount(bad)


class UnitsTests(unittest.TestCase):
    def test_equivalent_capacities(self):
        a, b = parse_spec_value("1TB"), parse_spec_value("1000 GB")
        self.assertTrue(spec_matches("eq", a, (b,)))
        self.assertFalse(spec_matches("eq", parse_spec_value("128GB"), (parse_spec_value("32GB"),)))

    def test_gte_and_uncomparable(self):
        self.assertTrue(spec_matches("gte", parse_spec_value("2 TB"), (parse_spec_value("1TB"),)))
        self.assertIsNone(spec_matches("gte", parse_spec_value("red"), (parse_spec_value("1TB"),)))
        self.assertIsNone(spec_matches("lte", parse_spec_value("5 kg"), (parse_spec_value("1TB"),)))

    def test_text_case_insensitive(self):
        self.assertTrue(spec_matches("in", parse_spec_value("NVMe  M.2"),
                                     (parse_spec_value("sata"), parse_spec_value("nvme m.2"))))


class IdTests(unittest.TestCase):
    def test_gtin(self):
        self.assertEqual(normalize_gtin("4006381333931"), "4006381333931")
        self.assertIsNone(normalize_gtin("4006381333932"))
        self.assertIsNone(normalize_gtin("123"))

    def test_merchant(self):
        self.assertEqual(merchant_id_from_url("https://WWW.Shop.Example.com./x"), "shop.example.com")
        for bad in ("", "ftp://a.com", "not a url", "https://"):
            with self.assertRaises(ValidationError, msg=bad):
                merchant_id_from_url(bad)


class IntentAndConfigTests(unittest.TestCase):
    def test_intent_validation(self):
        with self.assertRaises(ValidationError):
            UserIntent(description=" ", currency="USD")
        with self.assertRaises(ValidationError):
            UserIntent(description="x", currency="USD", quantity=0)
        with self.assertRaises(ValidationError):
            UserIntent(description="x", currency="USD", max_total=Money(100, "EUR"))
        with self.assertRaises(ValidationError):
            UserIntent(description="x", currency="USD", allowed_brands=frozenset({"A"}),
                       blocked_brands=frozenset({"a"}))
        with self.assertRaises(ValidationError):
            SpecConstraint("k", "eq", ("1", "2"))
        with self.assertRaises(ValidationError):
            ScoringWeights(Decimal(0), Decimal(0), Decimal(0))

    def test_env_overrides_and_errors(self):
        s = Settings.from_env({"TRUSSTED_EXTRACTION_MAX_RETRIES": "5", "TRUSSTED_EXTRACTION_SEED": ""})
        self.assertEqual(s.extraction.max_retries, 5)
        self.assertIsNone(s.extraction.seed)
        with self.assertRaises(ConfigError):
            Settings.from_env({"TRUSSTED_EXTRACTION_MAX_RETRIES": "abc"})
        with self.assertRaises(ConfigError):
            Settings.from_env({"TRUSSTED_EXTRACTION_MAX_RETRIES": "-1"})
        with self.assertRaises(ConfigError):
            RankConfig(missing_component_score=Decimal("2"))
        with self.assertRaises(ConfigError):
            Settings.from_env({"TRUSSTED_VERIFY_SEVERITIES": "x"})


if __name__ == "__main__":
    unittest.main()
