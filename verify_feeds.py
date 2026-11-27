"""Read-only direct checks of configured sources; never publishes."""
from datetime import datetime, timedelta, timezone
import urllib.request
from news_collector import SOURCES, parse_feed, _feed_entries, _entry_text, _entry_link, _entry_date


def main():
    failures = []
    for source, url in SOURCES.items():
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
        except Exception as error:
            failures.append(source)
            print(f"FAIL {source}: {error}", flush=True)
    if failures:
        raise SystemExit("Failed sources: " + ", ".join(failures))


if __name__ == "__main__":
    main()
