"""Read-only live checks for the two repaired sources; never invokes publishing."""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from news_collector import SOURCES, fetch_feed


def main():
    for source in ('The Times of Israel', 'China News Service [China mainland - state-affiliated]'):
        root, label = fetch_feed(source, SOURCES[source])
        items = root.findall('.//item')
        dates = []
        for item in items:
            assert item.findtext('title') and item.findtext('link'), 'Missing title/link'
            date = item.findtext('pubDate')
            if date:
                dates.append(parsedate_to_datetime(date))
        assert dates, 'Feed has no publication dates'
        latest = max(dates)
        assert latest >= datetime.now(timezone.utc) - timedelta(days=7), 'Feed is stale'
        print(f'PASS {label}: {len(items)} items; latest={latest.isoformat()}')


if __name__ == '__main__':
    main()
