import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ARCHIVE_FILE = "published_articles.json"
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
TELEGRAM_MESSAGE_LIMIT = 4096
ROME = ZoneInfo("Europe/Rome")
STATE_FILE = "publisher_state.json"
CYCLE_HOURS = (7, 9, 12, 14, 17, 19, 22)
CYCLE_MINUTES = (0, 30, 0, 30, 0, 30, 0)

def load_archive():
    try:
        with open(ARCHIVE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            state = json.load(file)
            return state if isinstance(state, dict) else {}
    except FileNotFoundError:
        return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)

def _title_key(value):
    return " ".join(str(value or "").casefold().split())

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

def article_group(article):
    text = (article.get("title", "") + " " + article.get("description", "")).casefold()
    conflict = any(x in text for x in ("war", "armed conflict", "military", "missile", "drone", "airstrike", "ceasefire", "battle", "invasion", "troops", "guerra", "conflitto", "attacco", "insurgent", "militant"))
    if conflict and any(x in text for x in ("ukraine", "ukrain", "russia", "russian", "moscow", "donbas")):
        return "russia_ukraine"
    if conflict and any(x in text for x in ("israel", "gaza", "palest", "hamas", "hezbollah", "lebanon", "syria", "yemen", "iran", "iraq", "west bank")):
        return "middle_east"
    return "rest_of_world"

def _theater_key(article):
    text = (article.get("title", "") + " " + article.get("description", "")).casefold()
    for key in ("ukrain", "russia", "gaza", "israel", "sudan", "somalia", "ethiopia", "congo", "myanmar", "haiti", "mexico", "afghanistan", "pakistan", "taiwan", "papua"):
        if key in text:
            return key
    return article.get("source", "")

def select_articles_for_cycle(articles, limit=6):
    """Return up to limit candidates, applying caps while preferring distinct theatres."""
    caps = {"russia_ukraine": 1, "middle_east": 1, "rest_of_world": 4}
    selected, used_theatres = [], set()
    remaining = list(articles)
    for prefer_unique in (True, False):
        for article in remaining:
            if len(selected) >= limit:
                break
            group = article_group(article)
            theatre = _theater_key(article)
            if caps[group] <= 0 or article in selected or (prefer_unique and theatre in used_theatres):
                continue
            selected.append(article); caps[group] -= 1; used_theatres.add(theatre)
    return selected

def iter_articles_for_cycle(articles):
    """Yield all eligible candidates in diversification order; failures can be backfilled."""
    caps = {"russia_ukraine": 1, "middle_east": 1, "rest_of_world": 4}
    used_theatres = set()
    remaining = list(articles)
    for prefer_unique in (True, False):
        for article in remaining:
            group = article_group(article)
            theatre = _theater_key(article)
            if caps[group] <= 0 or (prefer_unique and theatre in used_theatres):
                continue
            caps[group] -= 1
            used_theatres.add(theatre)
            yield article

def cycle_slot(now=None):
    local = (now or datetime.now(timezone.utc)).astimezone(ROME)
    for hour, minute in zip(CYCLE_HOURS, CYCLE_MINUTES):
        if local.hour == hour and minute <= local.minute < minute + 15:
            return local.strftime("%Y-%m-%d-%H%M")
    return None

def scheduled_cycle_due(now=None):
    """Allow delayed 15-minute Actions starts, with one persistent slot per local date."""
    local = (now or datetime.now(timezone.utc)).astimezone(ROME)
    for hour, minute in zip(CYCLE_HOURS, CYCLE_MINUTES):
        if hour == local.hour and minute <= local.minute < minute + 15:
            slot = f"{local.date().isoformat()}-{hour:02d}{minute:02d}"
            return slot not in set(load_state().get("completed_slots", []))
    return False

def publish_new_articles():
    from news_collector import collect_news
    archive = load_archive()
    known = {item.get("url") for item in archive if isinstance(item, dict)}
    known_titles = {_title_key(item.get("title")) for item in archive if isinstance(item, dict)}
    published_count = 0
    candidates = []
    seen_titles = set(known_titles)
    for article in collect_news():
        title_key = _title_key(article.get("title"))
        if article.get("url") in known or not title_key or title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        candidates.append(article)
    for article in iter_articles_for_cycle(candidates):
        if published_count >= 6:
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
    slot = cycle_slot(datetime.now(timezone.utc))
    if slot:
        state = load_state()
        completed = set(state.get("completed_slots", []))
        completed.add(slot)
        state["completed_slots"] = sorted(completed)[-64:]
        save_state(state)

if __name__ == "__main__":
    import sys
    if "--scheduled" in sys.argv and not scheduled_cycle_due():
        print("Nessun ciclo Prometheus previsto nell'orario locale corrente.")
        raise SystemExit(0)
    if DRY_RUN:
        print("PROMETHEUS PROTOCOL - MODALITA PROVA")
        print("Nessun messaggio verra inviato a Telegram.")
    else:
        publish_new_articles()

