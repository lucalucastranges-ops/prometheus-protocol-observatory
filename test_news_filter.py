import unittest

from news_collector import classify_article


class ThematicFilterTests(unittest.TestCase):
    def test_includes_security_relevant_article(self):
        included, reason = classify_article(
            "NATO rafforza la difesa sul fianco orientale",
            "Gli alleati annunciano nuove truppe e sistemi missilistici."
        )
        self.assertTrue(included)
        self.assertIn("guerra/difesa/conflitti", reason)

    def test_includes_energy_supply_article(self):
        included, _ = classify_article(
            "New gas pipeline changes regional energy security",
            "The project affects strategic energy supply."
        )
        self.assertTrue(included)

    def test_includes_strategic_maritime_article(self):
        included, _ = classify_article(
            "Shipping lanes disrupted near a key strait",
            "Commercial vessels are rerouted for security reasons."
        )
        self.assertTrue(included)

    def test_excludes_unrelated_politics(self):
        included, reason = classify_article(
            "Government announces election reform",
            "Parliament debates domestic campaign financing rules."
        )
        self.assertFalse(included)
        self.assertIn("nessuna implicazione", reason)

    def test_excludes_false_positive_context(self):
        included, reason = classify_article(
            "Football club signs a new star",
            "The team prepares for the championship."
        )
        self.assertFalse(included)
        self.assertIn("non pertinente", reason)

    def test_uses_title_and_description_together(self):
        included, _ = classify_article(
            "Government announces new measures",
            "The measures respond to an insurgency and internal security crisis."
        )
        self.assertTrue(included)


if __name__ == "__main__":
    unittest.main()