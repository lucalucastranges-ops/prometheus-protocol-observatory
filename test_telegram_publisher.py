import unittest

from telegram_publisher import _parse_json_object, prepare_message


class TelegramMessageTests(unittest.TestCase):
    def test_message_has_required_sections_and_original_link(self):
        message = prepare_message({
            "title_it": "Titolo in italiano",
            "summary_it": "Sintesi fedele dei fatti.",
            "strategic_relevance": "L'elemento può incidere sulla sicurezza regionale, ma la fonte non consente conclusioni ulteriori.",
            "source": "Fonte estera",
            "url": "https://example.com/original-article",
        })
        self.assertIn("Titolo in italiano", message)
        self.assertIn("Sintesi\n\nSintesi fedele dei fatti.", message)
        self.assertIn("Rilevanza strategica", message)
        self.assertIn("Fonte: Fonte estera", message)
        self.assertIn("Link originale: https://example.com/original-article", message)

    def test_analysis_is_omitted_when_insufficient(self):
        message = prepare_message({
            "title_it": "Titolo",
            "summary_it": "Fatto disponibile.",
            "strategic_relevance": "",
            "source": "Fonte",
            "url": "https://example.com/a",
        })
        self.assertNotIn("Rilevanza strategica", message)

    def test_message_limit_is_enforced(self):
        with self.assertRaises(ValueError):
            prepare_message({"title_it": "x" * 4090, "summary_it": "fatti", "source": "Fonte", "url": "https://example.com"})

    def test_json_parser_accepts_fenced_json(self):
        self.assertEqual(_parse_json_object('```json\n{"title_it":"Titolo","summary_it":"Fatto"}\n```')["title_it"], "Titolo")

    def test_duplicate_analysis_is_omitted(self):
        text = "Lo stesso testo"
        message = prepare_message({"title_it": "Titolo", "summary_it": text, "strategic_relevance": text, "source": "Fonte", "url": "https://example.com/a"})
        self.assertNotIn("Rilevanza strategica", message)


if __name__ == "__main__":
    unittest.main()

