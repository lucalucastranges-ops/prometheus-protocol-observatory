import json
import os
import urllib.request
from datetime import datetime, timezone

ARCHIVE_FILE = "published_articles.json"
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini")

def load_archive():
    try:
        with open(ARCHIVE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def generate_italian_summary(article):
    if not OPENAI_API_KEY:
        raise RuntimeError("Chiave API OpenAI non configurata")
    title = article.get("title", "")
    description = article.get("description", "")
    if not title or not description:
        raise ValueError("Titolo o descrizione mancanti")
    prompt = ("Sei un redattore di un osservatorio geopolitico. Scrivi in italiano un titolo e una sintesi di massimo 70 parole. Usa esclusivamente le informazioni fornite. Non inventare fatti, nomi, date o dichiarazioni. Mantieni un tono neutrale e giornalistico.

" f"Titolo originale: {title}
Descrizione originale: {description}")
    payload = {"model": OPENAI_MODEL, "input": prompt, "max_output_tokens": 220}
    request = urllib.request.Request("https://api.openai.com/v1/responses", data=json.dumps(payload).encode("utf-8"), headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    parts = [item.get("text", "") for output in result.get("output", []) for item in output.get("content", []) if item.get("type") == "output_text"]
    summary = "
".join(parts).strip()
    if not summary:
        raise RuntimeError("GPT non ha restituito una sintesi")
    return summary

def prepare_message(article):
    title = article.get("title", "Senza titolo")
    source = article.get("source", "Fonte sconosciuta")
    url = article.get("url", "")
    description = article.get("summary_it", "[Sintesi italiana non disponibile]")
    return f"{title}

{description}

Fonte: {source}
Approfondimento: {url}"

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
    payload = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
    request = urllib.request.Request(api_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError("Telegram non ha confermato l'invio.")
    return True

def publish_new_articles():
    from news_collector import collect_news
    archive = load_archive()
    known = {item.get("url") for item in archive if isinstance(item, dict)}
    for article in [a for a in collect_news() if a.get("url") not in known][:3]:
        article["summary_it"] = generate_italian_summary(article)
        if send_telegram_message(prepare_message(article)):
            archive.append({"url": article["url"], "title": article.get("title", ""), "source": article.get("source", ""), "published_at": datetime.now(timezone.utc).isoformat()})
            with open(ARCHIVE_FILE, "w", encoding="utf-8") as file:
                json.dump(archive, file, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if DRY_RUN:
        print("PROMETHEUS PROTOCOL - MODALITA PROVA")
        print("Nessun messaggio verra inviato a Telegram.")
    else:
        publish_new_articles()
