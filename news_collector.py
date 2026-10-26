import json
import urllib.request
import xml.etree.ElementTree as ET

SOURCES = {
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "The Guardian World": "https://www.theguardian.com/world/rss",
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
