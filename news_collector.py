import json
import urllib.request
import xml.etree.ElementTree as ET

SOURCES = {
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "The Guardian World": "https://www.theguardian.com/world/rss",
    "Al Jazeera English": "https://www.aljazeera.com/xml/rss/all.xml",
    "France 24": "https://www.france24.com/en/rss",
    "NHK Japan International": "https://www.nhk.or.jp/rss/news/cat6.xml",
    "The Hindu International": "https://www.thehindu.com/news/international/feeder/default.rss",
    "Al-Monitor": "https://www.al-monitor.com/rss",
    "Radio Free Europe": "https://www.rferl.org/api/zbqiml-vomx-tpeqkmy",
   
    "The Jerusalem Post": "https://www.jpost.com/rss/rssfeedsmiddleeastnews.aspx",
    "Agencia Brasil": "https://agenciabrasil.ebc.com.br/rss/internacional/feed.xml",
   
}

def collect_news():
    articles = []

    for source, url in SOURCES.items():
        print(f"Controllo fonte: {source}")

        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "PrometheusProtocolObservatory/0.1"}
            )

            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read()

            root = ET.fromstring(data)

            for item in root.findall(".//item")[:5]:
                title = item.findtext("title", default="").strip()
                link = item.findtext("link", default="").strip()

                if title and link:
                    articles.append({
                        "source": source,
                        "title": title,
                        "url": link,
                    })

        except Exception as error:
            print(f"Errore nella fonte {source}: {error}")

    return articles

if __name__ == "__main__":
    news = collect_news()
    print(f"Articoli raccolti: {len(news)}")
    print(json.dumps(news, ensure_ascii=False, indent=2))
