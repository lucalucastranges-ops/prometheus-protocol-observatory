import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone

ARCHIVE_FILE = "published_articles.json"
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
TELEGRAM_MESSAGE_LIMIT = 4096

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
    prompt = (
        "Sei un redattore geopolitico prudente. Rispondi esclusivamente con un oggetto JSON valido, senza markdown, con le chiavi "
        "title_it, summary_it e strategic_relevance. Scrivi tutto in italiano. title_it deve essere un titolo giornalistico accurato, "
        "chiaro e non sensazionalistico. summary_it deve riassumere fedelmente i fatti in 60-100 parole quando le informazioni lo consentono; "
        "se la fonte è scarna, resta proporzionato e dichiara il limite senza aggiungere dettagli. strategic_relevance deve contenere 30-50 parole "
        "di breve approfondimento basato soltanto su elementi documentati e inferenze esplicitamente caute; evita speculazioni, falsi virgolettati "
        "e fatti inventati. Non duplicare la sintesi. Se non ci sono elementi sufficienti per l'analisi, usa una stringa vuota. "
        "Titolo originale: " + title + ". Descrizione originale: " + description
    )
    for budget in (700, 1400):
        payload = {"model": OPENAI_MODEL, "input": prompt, "max_output_tokens": budget}
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": "Bearer " + OPENAI_API_KEY, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.load(response)
        parts = [
            part.get("text", "")
            for output in result.get("output", [])
            for part in output.get("content", [])
            if part.get("type") == "output_text"
        ]
        summary = " ".join(parts).strip()
        if summary:
            parsed = _parse_json_object(summary)
            if isinstance(parsed, dict) and isinstance(parsed.get("title_it"), str) and isinstance(parsed.get("summary_it"), str) and parsed["title_it"].strip() and parsed["summary_it"].strip():
                return {
                    "title_it": str(parsed["title_it"]).strip(),
                    "summary_it": str(parsed["summary_it"]).strip(),
                    "strategic_relevance": str(parsed.get("strategic_relevance", "")).strip(),
                }
        print("OpenAI: risposta senza testo; stato=" + str(result.get("status")) +
              "; motivo=" + str(result.get("incomplete_details")) +
              "; token=" + str(result.get("usage", {}).get("output_tokens")) +
              "; limite=" + str(budget), flush=True)
    raise RuntimeError("OpenAI non ha prodotto testo dopo due tentativi")

def _parse_json_object(text):
    """Accetta JSON puro e il solo involucro markdown che i modelli talvolta aggiungono."""
    candidate = text.strip()
    if candidate.startswith("```") and candidate.endswith("```"):
        candidate = candidate[3:-3].strip()
        if candidate.lower().startswith("json"):
            candidate = candidate[4:].strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(candidate[start:end + 1])
            except json.JSONDecodeError:
                pass
    return None

def prepare_message(article):
    title = article.get("title_it") or article.get("title", "Senza titolo")
    source = article.get("source", "Fonte sconosciuta")
    url = article.get("url", "")
    summary = article.get("summary_it", "[Sintesi italiana non disponibile]")
    relevance = str(article.get("strategic_relevance", "") or "").strip()
    if relevance and relevance.casefold() == str(summary).strip().casefold():
        relevance = ""
    sections = [title, "Sintesi", summary]
    if relevance:
        sections.extend(["Rilevanza strategica", relevance])
    sections.extend(["Fonte: " + source, "Link originale: " + url])
    message = "\n\n".join(sections)
    if len(message) > TELEGRAM_MESSAGE_LIMIT:
        raise ValueError("Messaggio oltre il limite Telegram di 4096 caratteri")
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
    api_url = "https://api.telegram.org/bot" + token + "/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
    request = urllib.request.Request(api_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError("Telegram non ha confermato l'invio.")
    return True

def select_articles_for_cycle(articles, limit=3):
    """Seleziona per fonte a rotazione, senza quote geografiche o priorità artificiali."""
    by_source = {}
    source_order = []
    for article in articles:
        source = article.get("source", "")
        if source not in by_source:
            by_source[source] = []
            source_order.append(source)
        by_source[source].append(article)

    selected = []
    while len(selected) < limit:
        added = False
        for source in source_order:
            if by_source[source]:
                selected.append(by_source[source].pop(0))
                added = True
                if len(selected) >= limit:
                    break
        if not added:
            break
    return selected

def publish_new_articles():
    from news_collector import collect_news
    archive = load_archive()
    known = {item.get("url") for item in archive if isinstance(item, dict)}
    published_count = 0
    candidates = [a for a in collect_news() if a.get("url") not in known]
    for article in select_articles_for_cycle(candidates, limit=3):
        if published_count >= 3:
            break
        if not article.get("title") or not article.get("description"):
            continue
        try:
            generated = generate_italian_summary(article)
            if not isinstance(generated, dict):
                raise ValueError("La risposta AI non contiene il formato strutturato richiesto")
            article.update(generated)
            if send_telegram_message(prepare_message(article)):
                archive.append({"url": article["url"], "title": article.get("title", ""), "source": article.get("source", ""), "published_at": datetime.now(timezone.utc).isoformat()})
                known.add(article["url"])
                published_count += 1
                with open(ARCHIVE_FILE, "w", encoding="utf-8") as file:
                    json.dump(archive, file, ensure_ascii=False, indent=2)
                print("Pubblicato: " + article["title"], flush=True)
        except Exception as error:
            print("Errore elaborazione/invio articolo: " + str(error), flush=True)
            if isinstance(error, urllib.error.HTTPError) and error.code in (401, 402, 403, 429):
                raise
    print("Articoli pubblicati in questo ciclo: " + str(published_count), flush=True)

if __name__ == "__main__":
    if DRY_RUN:
        print("PROMETHEUS PROTOCOL - MODALITA PROVA")
        print("Nessun messaggio verra inviato a Telegram.")
    else:
        publish_new_articles()

