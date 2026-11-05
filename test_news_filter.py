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


class RegressionTests(unittest.TestCase):
    def test_observed_run(self):
        import json
        from pathlib import Path
        cases = json.loads(Path("filter_regressions.json").read_text(encoding="utf-8"))
        for title, description, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(classify_article(title, description)[0], expected)

    def test_isolated_words_and_metaphors(self):
        for text in ("A battle with cancer", "Solar wins athletics medal",
                     "Port wine festival", "Gas cooking recipe", "Election in Taiwan"):
            with self.subTest(text=text):
                self.assertFalse(classify_article(text, "")[0])

    def test_clear_cases_do_not_call_ai(self):
        from unittest.mock import Mock
        reviewer = Mock()
        classify_article("Israeli attacks on Gaza kill nine people", "", reviewer)
        classify_article("Runner dies after battle with cancer", "", reviewer)
        reviewer.review.assert_not_called()

    def test_mixed_security_story_requires_review(self):
        from thematic_filter import local_decision
        self.assertIsNone(local_decision("Military attack on football stadium", "")[0])
        self.assertFalse(classify_article("Military attack on football stadium", "")[0])


    def test_compatibility_reviewer_argument_is_accepted(self):
        from unittest.mock import Mock
        reviewer = Mock()
        reviewer.review.return_value = (False, "test")
        included, reason = classify_article("Ambiguous security report", "Details need review.", reviewer)
        self.assertFalse(included)
        self.assertEqual(reason, "test")
        reviewer.review.assert_called_once_with("Ambiguous security report", "Details need review.")

    def test_ai_budget_cache_and_payload(self):
        import json
        from unittest.mock import patch, MagicMock
        from thematic_filter import ContextReviewer
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps({
                "relevant": True, "category": "security", "evidence": "security concerns"
            })}}]}).encode()
        reviewer = ContextReviewer()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}), patch(
                "urllib.request.urlopen", return_value=response) as network:
            for i in range(10):
                reviewer.review("security concerns " + str(i), "x" * 10000)
            reviewer.review("security concerns 0", "x" * 10000)
            self.assertEqual(network.call_count, 8)
            payload = json.loads(network.call_args.args[0].data)
            self.assertEqual(payload["max_completion_tokens"], 512)
            self.assertLessEqual(len(json.loads(payload["messages"][1]["content"])["description"]), 1400)
        self.assertEqual(reviewer.calls, 8)

    def test_ai_failures_are_closed_and_cached(self):
        from unittest.mock import patch
        from thematic_filter import ContextReviewer
        reviewer = ContextReviewer()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}), patch(
                "urllib.request.urlopen", side_effect=ValueError("bad response")) as network:
            self.assertFalse(reviewer.review("security concerns", "")[0])
            self.assertFalse(reviewer.review("security concerns", "")[0])
            self.assertEqual(network.call_count, 1)

    def test_ai_requires_evidence_and_valid_boolean(self):
        import json
        from unittest.mock import patch, MagicMock
        from thematic_filter import ContextReviewer
        for verdict in ({"relevant": "true", "category": "security", "evidence": "security concerns"},
                        {"relevant": True, "category": "security", "evidence": "invented quotation"},
                        {"relevant": True, "category": "sports", "evidence": "security concerns"}):
            response = MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps({
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(verdict)}}]
            }).encode()
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}), patch(
                    "urllib.request.urlopen", return_value=response):
                self.assertFalse(ContextReviewer().review("security concerns", "")[0])

if __name__ == "__main__":
    unittest.main()
