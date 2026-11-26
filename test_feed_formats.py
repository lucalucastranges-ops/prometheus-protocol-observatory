import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo

import news_collector as nc


class FeedFormatTests(unittest.TestCase):
    def test_rdf(self):
        root = ET.fromstring("""<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:dc="http://purl.org/dc/elements/1.1/"><item><title>Sudan military conflict</title><link>https://example.org/a</link><dc:date>2026-11-26T07:00:00Z</dc:date></item></rdf:RDF>""")
        entry = nc._feed_entries(root)[0]
        self.assertEqual(nc._entry_link(entry), "https://example.org/a")
        self.assertEqual(nc._entry_date(entry).year, 2026)

    def test_atom(self):
        root = ET.fromstring("""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Military ceasefire</title><link rel="alternate" href="https://example.org/b"/><updated>2026-11-26T07:00:00Z</updated><summary>Troops agree to ceasefire</summary></entry></feed>""")
        entry = nc._feed_entries(root)[0]
        self.assertEqual(nc._entry_link(entry), "https://example.org/b")
        self.assertEqual(nc._entry_text(entry, "summary"), "Troops agree to ceasefire")

    def test_rss(self):
        root = ET.fromstring("""<rss><channel><item><title>Military attack</title><link>https://example.org/c</link><pubDate>Thu, 26 Nov 2026 07:00:00 GMT</pubDate></item></channel></rss>""")
        entry = nc._feed_entries(root)[0]
        self.assertEqual(nc._entry_date(entry).year, 2026)

    def test_invalid_date(self):
        root = ET.fromstring("<item><pubDate>invalid</pubDate></item>")
        self.assertIsNone(nc._entry_date(root))


if __name__ == "__main__":
    unittest.main()
