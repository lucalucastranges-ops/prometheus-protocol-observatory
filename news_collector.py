import json
import urllib.request
import xml.etree.ElementTree as ET
import html
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

def clean_description(text):
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = " ".join(text.split())
    return text

def load_published_articles():
    try:
        with open("published_articles.json", "r", encoding="utf-8") as file:
            records = json.load(file)
    except FileNotFoundError:
        return set()
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent_urls = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        try:
            published_at = datetime.fromisoformat(record["published_at"])
            if published_at.tzinfo is None:
                continue
            if published_at >= cutoff:
                recent_urls.add(record["url"])
        except (KeyError, TypeError, ValueError):
            continue
    return recent_urls

def clean_published_articles():
    try:
        with open("published_articles.json", "r", encoding="utf-8") as file:
            records = json.load(file)
    except FileNotFoundError:
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent_records = []
    for record in records:
        if not isinstance(record, dict):
            continue
        try:
            published_at = datetime.fromisoformat(record["published_at"])
            if published_at.tzinfo is not None and published_at >= cutoff:
                recent_records.append(record)
        except (KeyError, TypeError, ValueError):
            continue
    with open("published_articles.json", "w", encoding="utf-8") as file:
        json.dump(recent_records, file, ensure_ascii=False, indent=2)

SOURCES = {
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "BBC Africa": "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
    "The Guardian World": "https://www.theguardian.com/world/rss",
    "France 24": "https://www.france24.com/en/rss",
    "France 24 Americas": "https://www.france24.com/en/americas/rss",
    "NHK Japan International": "https://www.nhk.or.jp/rss/news/cat6.xml",
    "The Hindu International": "https://www.thehindu.com/news/international/feeder/default.rss",
    "Al-Monitor": "https://www.al-monitor.com/rss",
    "Radio Free Europe": "https://www.rferl.org/api/zbqiml-vomx-tpeqkmy",
    "The Jerusalem Post": "https://www.jpost.com/rss/rssfeedsmiddleeastnews.aspx",
    "Agencia Brasil": "https://agenciabrasil.ebc.com.br/rss/internacional/feed.xml",
    "Africanews": "https://www.africanews.com/feed/async/",
    "The Times of Israel": "https://www.timesofisrael.com/feed/",
    "China News Service": "https://www.chinanews.com.cn/rss/world.xml",
    "CCTV News": "http://www.cctv.com/program/rss/02/02/index.xml",
    "Focus Taiwan/CNA (Google News RSS relay)": "https://news.google.com/rss/search?q=site%3Afocustaiwan.tw&hl=en&gl=US&ceid=US:en",
    "Daily Sabah": "https://www.dailysabah.com/rss/turkey",
    "AllAfrica": "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf",
    "SABC News": "https://www.sabcnews.com/sabcnews/feed/",
    "Foreign Policy": "https://foreignpolicy.com/feed/",
}

from thematic_filter import classify_article, ContextReviewer

def collect_news():
    articles = []
    reviewer = ContextReviewer()
    seen_urls = set()
    for source, url in SOURCES.items():
        print(f"Controllo fonte: {source}")
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "PrometheusProtocolObservatory/0.1"})
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read()
            root = ET.fromstring(data)
            def local_name(tag):
                return tag.rsplit("}", 1)[-1]

            def child_text(element, name):
                for child in element:
                    if local_name(child.tag) == name:
                        return (child.text or "").strip()
                return ""

            for item in (element for element in root.iter() if local_name(element.tag) == "item"):
                title = child_text(item, "title")
                link = child_text(item, "link")
                date_text = child_text(item, "pubDate") or child_text(item, "date")
                if not date_text:
                    continue
                try:
                    published = parsedate_to_datetime(date_text)
                    if published.tzinfo is None:
                        published = published.replace(tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    continue
                if published.astimezone(ZoneInfo("Europe/Rome")).date() != datetime.now(ZoneInfo("Europe/Rome")).date():
                    continue
                description = clean_description(item.findtext("description", default=""))
                if title and link and link not in seen_urls:
                    included, reason = classify_article(title, description, reviewer)
                    print(f"Filtro tematico: {'INCLUSO' if included else 'ESCLUSO'} - {title} - {reason}")
                    if not included:
                        continue
                    articles.append({"source": source, "title": title, "url": link, "description": description, "published_at": published.isoformat()})
                    seen_urls.add(link)
        except Exception as error:
            print(f"Errore nella fonte {source}: {error}")
    return articles

if __name__ == "__main__":
    news = collect_news()
    print(f"Articoli raccolti: {len(news)}")
    print(json.dumps(news, ensure_ascii=False, indent=2))
