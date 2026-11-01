"""Offline replay of run 41322115507. No credentials, API calls or archive writes."""
import json
from pathlib import Path
from unittest.mock import patch

from news_collector import classify_article
import telegram_publisher as publisher


def main():
    cases = json.loads(Path(__file__).with_name("filter_regressions.json").read_text(encoding="utf-8"))
    articles = []
    for i, (title, description, expected) in enumerate(cases):
        included, reason = classify_article(title, description)
        assert included == expected, title
        print(("INCLUSO" if included else "ESCLUSO") + " - " + title + " - " + reason)
        if included:
            articles.append({"title": title, "description": description or title,
                             "url": "https://example.invalid/" + str(i), "source": "replay"})
    selected = publisher.select_articles_for_cycle(articles)
    assert len(selected) == 3
    # Exercise the actual publisher loop with external effects blocked.
    with patch.object(publisher, "DRY_RUN", True), patch.object(publisher, "load_archive", return_value=[]), patch(
            "news_collector.collect_news", return_value=articles), patch.object(
            publisher, "generate_italian_summary", side_effect=lambda a: "[SIMULAZIONE] " + a["title"]), patch(
            "urllib.request.urlopen", side_effect=AssertionError("Network forbidden")), patch(
            "builtins.open", side_effect=AssertionError("Archive write forbidden")):
        publisher.publish_new_articles()
    print("Simulazione completata: 3 selezionati, 0 invii, 0 scritture archivio, 0 chiamate AI.")


if __name__ == "__main__":
    main()
