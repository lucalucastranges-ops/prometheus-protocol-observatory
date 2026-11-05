import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import news_collector as collector
import telegram_publisher as publisher


def article(number, source='A'):
    return dict(title=f'Article {number}', description='Documented conflict report.',
                source=source, url=f'https://example.com/{number}')


GENERATED = dict(title_it='Titolo italiano', summary_it='Fatti documentati.',
                 strategic_relevance='Possibili implicazioni regionali.')


def response(status='completed', text=None, **extra):
    return io.BytesIO(json.dumps(dict(status=status, output=[dict(content=[
        dict(type='output_text', text=json.dumps(GENERATED) if text is None else text)
    ])], **extra)).encode())


class GenerationRegressions(unittest.TestCase):
    def generate(self, responses):
        with patch.object(publisher, 'OPENAI_API_KEY', 'test'), patch.object(
                publisher.urllib.request, 'urlopen', side_effect=responses) as request:
            result = publisher.generate_italian_summary(article(1))
        return result, request

    def test_strict_schema_and_minimal_reasoning(self):
        result, request = self.generate([response()])
        self.assertEqual(result, GENERATED)
        payload = json.loads(request.call_args.args[0].data)
        self.assertEqual(payload['reasoning'], {'effort': 'minimal'})
        self.assertTrue(payload['text']['format']['strict'])
        self.assertEqual(set(payload['text']['format']['schema']['required']), set(GENERATED))
        self.assertEqual(payload['max_output_tokens'], 900)
        self.assertEqual(request.call_count, 1)

    def test_incomplete_even_valid_json_must_retry(self):
        result, request = self.generate([response('incomplete'), response()])
        self.assertEqual(result, GENERATED)
        self.assertEqual([json.loads(c.args[0].data)['max_output_tokens']
                          for c in request.call_args_list], [900, 1200])

    def test_truncated_json_and_wrong_types_retry(self):
        for invalid in ['{"title_it":', json.dumps(dict(GENERATED, strategic_relevance=None))]:
            with self.subTest(invalid=invalid):
                result, request = self.generate([response(text=invalid), response()])
                self.assertEqual(result, GENERATED)
                self.assertEqual(request.call_count, 2)

    def test_two_failures_are_bounded(self):
        with self.assertRaises(RuntimeError):
            self.generate([response('incomplete', ''), response('incomplete', '')])

    def test_refusal_is_not_retried(self):
        refused = io.BytesIO(json.dumps(dict(status='completed', output=[dict(content=[
            dict(type='refusal', refusal='Refused')])])).encode())
        with patch.object(publisher, 'OPENAI_API_KEY', 'test'), patch.object(
                publisher.urllib.request, 'urlopen', return_value=refused) as request:
            with self.assertRaises(ValueError):
                publisher.generate_italian_summary(article(1))
            self.assertEqual(request.call_count, 1)


class PublicationRegressions(unittest.TestCase):
    def test_replaces_failures_and_avoids_archive_and_cycle_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'archive.json'
            path.write_text(json.dumps([article(0)]))
            candidates = [article(0), dict(article(0), url="https://relay.example.com/archived"), article(1), article(2), article(3), article(3),
                          article(4), article(5), article(6)]
            with patch.object(publisher, 'ARCHIVE_FILE', str(path)), patch.object(
                    publisher, 'DRY_RUN', False), patch.object(publisher, 'generate_italian_summary',
                    side_effect=[ValueError('AI failed'), GENERATED, GENERATED, GENERATED, GENERATED]) as ai, patch.object(
                    publisher, 'send_telegram_message', side_effect=[False, True, True, True]) as send:
                self.assertEqual(publisher.publish_new_articles(candidates), 4)
            saved = json.loads(path.read_text())
            self.assertEqual([row['url'] for row in saved], [article(n)['url'] for n in [0, 3, 4, 5]])
            self.assertEqual(ai.call_count, 6)
            self.assertEqual(send.call_count, 4)
            self.assertNotIn('title_it', candidates[3])

    def test_dry_run_reaches_three_without_send_or_archive_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'archive.json'
            path.write_text(json.dumps([article(0)]))
            before = path.read_bytes()
            with patch.object(publisher, 'ARCHIVE_FILE', str(path)), patch.object(
                    publisher, 'DRY_RUN', True), patch.object(publisher, 'generate_italian_summary',
                    side_effect=[ValueError('AI failed'), GENERATED, GENERATED, GENERATED]) as ai, patch.object(
                    publisher, 'send_telegram_message') as send:
                result = publisher.publish_new_articles([article(n) for n in range(6)])
                self.assertEqual(result, 3)
                send.assert_not_called()
                self.assertEqual(ai.call_count, 5)
            self.assertEqual(path.read_bytes(), before)

    def test_exhausted_candidates_and_rotation(self):
        candidates = [article(1), article(2), article(3, 'B'), article(4, 'B')]
        self.assertEqual([a['title'] for a in publisher.select_articles_for_cycle(candidates, 4)],
                         ['Article 1', 'Article 3', 'Article 2', 'Article 4'])
        with patch.object(publisher, 'load_archive', return_value=[]), patch.object(
                publisher, 'DRY_RUN', True), patch.object(publisher, 'generate_italian_summary', return_value=GENERATED):
            self.assertEqual(publisher.publish_new_articles(candidates[:1]), 1)

    def test_missing_data_is_skipped(self):
        with patch.object(publisher, 'load_archive', return_value=[]), patch.object(
                publisher, 'generate_italian_summary') as ai:
            self.assertEqual(publisher.publish_new_articles([{}, dict(article(1), description='')]), 0)
            ai.assert_not_called()


class FeedRegressions(unittest.TestCase):
    def test_gbk_xml(self):
        data = '<?xml version="1.0" encoding="GBK"?><rss><channel><item><title>国际新闻</title></item></channel></rss>'
        self.assertEqual(collector.parse_feed(data.encode('gbk')).findtext('.//title'), '国际新闻')

    def test_403_fallback_and_attribution(self):
        feed = b'<rss><channel><item><title>News</title></item></channel></rss>'
        error = urllib.error.HTTPError('https://example.com', 403, 'Forbidden', {}, None)
        with patch.object(collector.urllib.request, 'urlopen', side_effect=[error, io.BytesIO(feed)]) as request:
            root, label = collector.fetch_feed('The Times of Israel', collector.SOURCES['The Times of Israel'])
        self.assertIn('Google News RSS relay', label)
        self.assertEqual(request.call_count, 2)
        self.assertTrue(request.call_args.args[0].full_url.startswith('https://news.google.com/rss/'))
        self.assertEqual(root.findtext('.//title'), 'News')

    def test_direct_feed_and_unrecoverable_failure(self):
        with patch.object(collector.urllib.request, 'urlopen', return_value=io.BytesIO(b'<rss><item/></rss>')) as request:
            _, label = collector.fetch_feed('The Times of Israel', collector.SOURCES['The Times of Israel'])
            self.assertEqual(label, 'The Times of Israel')
            self.assertEqual(request.call_count, 1)
        with patch.object(collector.urllib.request, 'urlopen', side_effect=OSError('offline')) as request:
            with self.assertRaises(OSError):
                collector.fetch_feed('The Times of Israel', collector.SOURCES['The Times of Israel'])
            self.assertEqual(request.call_count, 2)
