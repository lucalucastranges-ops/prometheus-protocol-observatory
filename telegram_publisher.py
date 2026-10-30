
import json
import os
import urllib.request
from datetime import datetime, timezone

ARCHIVE_FILE = "published_articles.json"

# Modalità prova: nessuna pubblicazione su Telegram
DRY_RUN = True



def load_archive():
    try:
        with open(ARCHIVE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def preview_article(article):
    title = article.get("title", "Senza titolo")
    source = article.get("source", "Fonte sconosciuta")
    url = article.get("url", "")

    print("ANTEPRIMA - NON PUBBLICATO")
    print(title)
    print("Fonte:", source)
    print("Link:", url)





def prepare_message(article):
    title = article.get("title", "Senza titolo")
    source = article.get("source", "Fonte sconosciuta")
    url = article.get("url", "")
    description = article.get("description", "")
    message = (
    f"{title}\n\n"
    f"{description}\n\n"
    f"Fonte: {source}\n"
    f"Approfondimento: {url}"
)

    return message


def send_telegram_message(message):
    if DRY_RUN:
        print("MODALITA PROVA - INVIO BLOCCATO")
        print(message)
        return False

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError("Credenziali Telegram mancanti.")

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = json.dumps({
        "chat_id": chat_id,
        "text": message
    }).encode("utf-8")

    request = urllib.request.Request(
        api_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.load(response)

    if not result.get("ok"):
        raise RuntimeError("Telegram non ha confermato l'invio.")

    return True

def preview_collected_news():
    from news_collector import collect_news

    articles = collect_news()
    print(f"Notizie raccolte: {len(articles)}")

    for article in articles[:3]:
        preview_article(article)

    return articles


if __name__ == "__main__":
    if DRY_RUN:
        print("PROMETHEUS PROTOCOL - MODALITA PROVA")
        print("Nessun messaggio verra inviato a Telegram.")
        preview_collected_news()
    else:
        raise RuntimeError("Pubblicazione non ancora abilitata.")
