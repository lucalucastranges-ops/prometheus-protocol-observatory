
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


if __name__ == "__main__":
    if DRY_RUN:
        print("PROMETHEUS PROTOCOL - MODALITA PROVA")
        print("Nessun messaggio verra inviato a Telegram.")
    else:
        raise RuntimeError("Pubblicazione non ancora abilitata.")


def prepare_message(article):
    title = article.get("title", "Senza titolo")
    source = article.get("source", "Fonte sconosciuta")
    url = article.get("url", "")

    message = (
        f"{title}\n\n"
        f"Fonte: {source}\n"
        f"Approfondimento: {url}"
    )

    return message

