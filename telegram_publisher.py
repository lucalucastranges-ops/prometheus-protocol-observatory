
import json
import os
import urllib.request
from datetime import datetime, timezone
import urllib.error

ARCHIVE_FILE = "published_articles.json"

# Modalità prova: nessuna pubblicazione su Telegram
DRY_RUN = True
# Configurazione GPT per le sintesi geopolitiche
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-5.4-nano"


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





def generate_italian_summary(article):
    if not OPENAI_API_KEY:
        raise RuntimeError("Chiave API OpenAI non configurata")

    title = article.get("title", "")
    description = article.get("description", "")

    if not title or not description:
        raise ValueError("Titolo o descrizione mancanti")

    prompt = (
        "Sei un redattore di un osservatorio geopolitico. "
        "Scrivi in italiano un titolo e una sintesi di massimo 70 parole. "
        "Usa esclusivamente le informazioni fornite. "
        "Non inventare fatti, nomi, date o dichiarazioni. "
        "Mantieni un tono neutrale e giornalistico.\n\n"
        f"Titolo originale: {title}\n"
        f"Descrizione originale: {description}"
    )

    payload = {
        "model": OPENAI_MODEL,
        "input": prompt,
        "max_output_tokens": 220
    }

    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)

    parts = [
        item.get("text", "")
        for output in result.get("output", [])
        for item in output.get("content", [])
        if item.get("type") == "output_text"
    ]

    summary = "\n".join(parts).strip()
    if not summary:
        raise RuntimeError("GPT non ha restituito una sintesi")

    return summary

def prepare_message(article):
    title = article.get("title", "Senza titolo")
    source = article.get("source", "Fonte sconosciuta")
    url = article.get("url", "")
    description = article.get("summary_it", "")
    if not description:
        description = "[ANTEPRIMA - Sintesi italiana non ancora generata]"
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
        article["summary_it"] = generate_italian_summary(article)
        
        message = prepare_message(article)
        print("ANTEPRIMA MESSAGGIO TELEGRAM - NON PUBBLICATO\n", message)

    return articles


if __name__ == "__main__":
    if DRY_RUN:
        print("PROMETHEUS PROTOCOL - MODALITA PROVA")
        print("Nessun messaggio verra inviato a Telegram.")
        preview_collected_news()
    else:
        raise RuntimeError("Pubblicazione non ancora abilitata.")
