"""Read-only direct feed health checks; no publishing or archive writes."""
from datetime import datetime, timedelta, timezone
import time
import urllib.request
from news_collector import SOURCES, parse_feed, _feed_entries, _entry_text, _entry_link, _entry_date


def check_source(source, url):
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "PrometheusProtocolObservatory/0.1"})
            with urllib.request.urlopen(request, timeout=15) as response:
                root = parse_feed(response.read())
            entries = _feed_entries(root)
            dates = [_entry_date(item) for item in entries if _entry_text(item, "title") and _entry_link(item)]
            dates = [date for date in dates if date is not None]
            if not dates or max(dates) < datetime.now(timezone.utc) - timedelta(days=7):
                raise ValueError("Missing or stale dated entries")
            print(f"PASS {source}: {len(entries)} entries", flush=True)
            return True
        except Exception as error:
            print(f"Attempt {attempt + 1}/3 {source}: {error}", flush=True)
            if attempt < 2:
                time.sleep(2 ** attempt)
    print(f"::warning::Unavailable source: {source}", flush=True)
    return False


def main():
    failures = [source for source, url in SOURCES.items() if not check_source(source, url)]
    healthy = len(SOURCES) - len(failures)
    print(f"Feed health: {healthy}/{len(SOURCES)}; unavailable: {', '.join(failures)}", flush=True)
    if not SOURCES or healthy * 2 < len(SOURCES):
        raise SystemExit("Critical feed availability: fewer than half healthy")


if __name__ == "__main__":
    main()
