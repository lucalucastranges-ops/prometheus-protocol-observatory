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
    "The Times of Israel [Israel - independent]": "https://www.timesofisrael.com/feed/",
    "The Times of Israel": "https://www.timesofisrael.com/feed/",
    "China News Service [China mainland - state-affiliated]": "https://www.chinanews.com.cn/rss/world.xml",
    "CCTV News [China mainland - state media]": "http://www.cctv.com/program/rss/02/02/index.xml",
    "Focus Taiwan / CNA [Taiwan - public news agency]": "https://focustaiwan.tw/rss",
    "Daily Sabah [Turkey - pro-government]": "https://www.dailysabah.com/rss/turkey",
    "Agencia Brasil": "https://agenciabrasil.ebc.com.br/rss/internacional/feed.xml",
    "Africanews": "https://www.africanews.com/feed/async/",
    "AllAfrica [Africa - independent aggregator]": "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf",
    "SABC News [South Africa - public broadcaster]": "https://www.sabcnews.com/sabcnews/feed/",
    "Foreign Policy [United States - independent specialist]": "https://foreignpolicy.com/feed/",
    "ReliefWeb [humanitarian situation reports]": "https://reliefweb.int/updates/rss.xml",
    "The New Humanitarian [specialist journalism]": "https://www.thenewhumanitarian.org/rss",
    "InSight Crime [Latin America organized crime]": "https://insightcrime.org/feed/",
    "RNZ Pacific [Pacific regional broadcaster]": "https://www.rnz.co.nz/rss/world.xml",
}

# Filtro locale, deterministico e senza costi API: richiede segnali contestuali
# nel titolo o nella descrizione, invece di accettare una singola parola isolata.
THEMATIC_GROUPS = {
    "guerra/difesa/conflitti": (r"\bwar(?:fare)?\b", r"armed conflict", r"military", r"defen[cs]e", r"weapon", r"missile", r"drone strike", r"airstrike", r"ceasefire", r"battle", r"invasion", r"front line", r"troops", r"nato", r"guerra", r"conflitto", r"difesa", r"armamenti", r"missili", r"truppe"),
    "sicurezza interna": (r"terror(?:ism|ist)", r"insurgenc", r"coup", r"state of emergency", r"internal security", r"civil unrest", r"militant attack", r"jihad", r"terrorismo", r"terroristi", r"insurrez", r"colpo di stato", r"ordine pubblico", r"sicurezza interna"),
    "energia/approvvigionamenti strategici": (r"\boil\b", r"\bgas\b", r"lng", r"nuclear", r"renewable", r"solar", r"wind power", r"critical mineral", r"rare earth", r"uranium", r"energy supply", r"energy security", r"pipeline", r"petrolio", r"nucleare", r"rinnovabili", r"minerali critici", r"terre rare", r"approvvigionamento"),
    "infrastrutture e corridoi strategici": (r"\bport\b", r"\bstrait\b", r"shipping lane", r"trade route", r"maritime", r"oil pipeline", r"gas pipeline", r"logistics corridor", r"strategic infrastructure", r"porto", r"stretto", r"rotta marittima", r"rotte commerciali", r"gasdotto", r"oleodotto", r"corridoio logistico", r"infrastrutture strategiche"),
}
EXCLUDED_CONTEXTS = (r"football|soccer|celebrity|entertainment|recipe|fashion|lifestyle|\bweather\b",)

def parse_feed(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    try:
        return ET.fromstring(data)
    except (ET.ParseError, ValueError):
        return ET.fromstring(data.decode("gbk"))

def fetch_feed(source, url):
    request = urllib.request.Request(url, headers={"User-Agent": "PrometheusProtocolObservatory/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return parse_feed(response.read()), source
    except Exception as first:
        relay = "https://news.google.com/rss/search?q=" + urllib.parse.quote(source)
        request = urllib.request.Request(relay, headers={"User-Agent": "PrometheusProtocolObservatory/0.1"})
        with urllib.request.urlopen(request, timeout=15) as response:
            return parse_feed(response.read()), source + " [Google News RSS relay]"

def classify_article(title, description, reviewer=None):
    from thematic_filter import classify_article as contextual_classify
    return contextual_classify(title, description, reviewer)

def _entry_text(item, name):
    """Read RSS/RDF or Atom fields without relying on namespace prefixes."""
    for child in item:
        if child.tag.rsplit("}", 1)[-1] == name:
            return "".join(child.itertext()).strip()
    return ""


def _feed_entries(root):
    return [element for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] in ("item", "entry")]


def _entry_link(item):
    for child in item:
        if child.tag.rsplit("}", 1)[-1] == "link":
            href = child.get("href")
            if href and child.get("rel", "alternate") == "alternate":
                return href.strip()
            if child.text and child.text.strip():
                return child.text.strip()
    return ""


def _entry_date(item):
    raw = (_entry_text(item, "pubDate") or _entry_text(item, "published")
           or _entry_text(item, "updated") or _entry_text(item, "date"))
    if not raw:
        return None
    try:
        date = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        try:
            date = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date


def collect_news():
    articles = []
    seen_urls = set()
    today = datetime.now(ZoneInfo("Europe/Rome")).date()
    for source, url in SOURCES.items():
        stats = {"entries": 0, "outdated": 0, "undated": 0,
                 "excluded": 0, "included": 0}
        print(f"Controllo fonte: {source}", flush=True)
        try:
            # Use the configured feed directly. A Google News search is not
            # an authenticated substitute for an outlet's own RSS feed.
            request = urllib.request.Request(
                url, headers={"User-Agent": "PrometheusProtocolObservatory/0.1"})
            with urllib.request.urlopen(request, timeout=15) as response:
                root = parse_feed(response.read())
            for item in _feed_entries(root):
                stats["entries"] += 1
                published = _entry_date(item)
                if published is None:
                    stats["undated"] += 1
                    continue
                if published.astimezone(ZoneInfo("Europe/Rome")).date() != today:
                    stats["outdated"] += 1
                    continue
                title = _entry_text(item, "title")
                link = _entry_link(item)
                description = clean_description(
                    _entry_text(item, "description")
                    or _entry_text(item, "summary")
                    or _entry_text(item, "content"))
                if not title or not link or link in seen_urls:
                    continue
                included, reason = classify_article(title, description)
                print(f"Filtro tematico: {'INCLUSO' if included else 'ESCLUSO'} - {title} - {reason}")
                if not included:
                    stats["excluded"] += 1
                    continue
                articles.append({"source": source, "title": title, "url": link,
                                 "description": description,
                                 "published_at": published.isoformat()})
                seen_urls.add(link)
                stats["included"] += 1
        except Exception as error:
            print(f"Errore nella fonte {source}: {error}", flush=True)
        finally:
            print(f"Riepilogo fonte {source}: {stats}", flush=True)
    return articles


if __name__ == "__main__":
    news = collect_news()
    print(f"Articoli raccolti: {len(news)}")
    print(json.dumps(news, ensure_ascii=False, indent=2))

