import unittest

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from unittest.mock import patch
from telegram_publisher import _parse_json_object, prepare_message, select_articles_for_cycle, iter_articles_for_cycle, cycle_slot, scheduled_cycle_slot, scheduled_cycle_due


class TelegramMessageTests(unittest.TestCase):
    def test_strict_geographic_caps_and_underfill(self):
        articles = [{"title": x, "description": x, "url": str(i)} for i, x in enumerate([
            "Russia Ukraine front", "Gaza Israel ceasefire", "Iran ceasefire", "Sudan armed conflict", "Myanmar conflict",
            "Haiti armed conflict", "Somalia insurgency", "Ethiopia conflict", "Taiwan security"
        ])]
        selected = select_articles_for_cycle(articles)
        self.assertEqual(len(selected), 6)
        self.assertEqual(sum("russia_ukraine" == __import__("telegram_publisher").article_group(a) for a in selected), 1)
        self.assertEqual(sum("middle_east" == __import__("telegram_publisher").article_group(a) for a in selected), 2)
        self.assertEqual(sum("rest_of_world" == __import__("telegram_publisher").article_group(a) for a in selected), 3)

    def test_five_daily_slots_in_rome_winter_and_summer(self):
        with patch("telegram_publisher.load_state", return_value={}):
            for hour, minute in ((7, 30), (12, 30), (15, 0), (17, 30), (22, 30)):
                for month in (1, 7):
                    local = datetime(2026, month, 15, hour, minute, tzinfo=ZoneInfo("Europe/Rome"))
                    self.assertEqual(scheduled_cycle_slot(local), f"2026-{month:02d}-15-{hour:02d}{minute:02d}")
                    self.assertTrue(scheduled_cycle_due(local))

    def test_recover_first_uncompleted_slot_and_no_previous_day(self):
        with patch("telegram_publisher.load_state", return_value={}):
            self.assertIsNone(scheduled_cycle_slot(datetime.fromisoformat("2026-11-27T05:50:00+00:00")))
            self.assertEqual(scheduled_cycle_slot(datetime.fromisoformat("2026-11-27T10:20:00+00:00")), "2026-11-27-0730")
            self.assertEqual(scheduled_cycle_slot(datetime.fromisoformat("2026-11-27T14:10:00+00:00")), "2026-11-27-0730")
            self.assertEqual(scheduled_cycle_slot(datetime.fromisoformat("2026-11-27T22:55:00+00:00")), "2026-11-27-2230")
            self.assertIsNone(scheduled_cycle_slot(datetime.fromisoformat("2026-11-28T06:10:00+00:00")))
        with patch("telegram_publisher.load_state", return_value={"completed_slots": ["2026-11-27-0730"]}):
            self.assertEqual(scheduled_cycle_slot(datetime.fromisoformat("2026-11-27T14:10:00+00:00")), "2026-11-27-0930")

    def test_geographic_word_without_conflict_does_not_override_group(self):
        article = {"title": "Russia discusses gas pipeline", "description": "Energy supply talks continue."}
        self.assertEqual(__import__("telegram_publisher").article_group(article), "rest_of_world")

    def test_candidate_iterator_does_not_consume_caps_before_success(self):
        articles = [{"title": "Sudan armed conflict", "description": "x", "url": "1"},
                    {"title": "Sudan armed conflict follow-up", "description": "x", "url": "2"},
                    {"title": "Myanmar conflict", "description": "x", "url": "3"}]
        candidates = list(iter_articles_for_cycle(articles))
        self.assertEqual(len(candidates), 3)

    def test_duplicate_urls_and_titles_are_filtered_by_publisher_inputs(self):
        self.assertEqual(__import__("telegram_publisher")._title_key("  Same   title "), "same title")

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

