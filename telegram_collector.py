import json
import re
import urllib.request
from html import unescape
from html.parser import HTMLParser

CHANNEL = "estero24hnews"
URL = f"https://t.me/s/{CHANNEL}"
MAX_MESSAGES = 10


class TelegramParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.messages = []
        self.current = None
        self.text_depth = 0
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get("class", "").split()

        if "tgme_widget_message" in classes:
            message_id = attributes.get("data-post", "")
            if message_id.startswith(CHANNEL + "/"):
                self.current = {
                    "source": "Estero 24H",
                    "url": f"https://t.me/{message_id}",
                    "date": "",
                    "text": ""
                }

        if self.current is None:
            return

        if tag == "time" and "datetime" in attributes:
            self.current["date"] = attributes["datetime"]

        if "tgme_widget_message_text" in classes:
            self.text_depth = 1
            self.text_parts = []
        elif self.text_depth:
            self.text_depth += 1
            if tag == "br":
                self.text_parts.append("\n")

    def handle_data(self, data):
        if self.current is not None and self.text_depth:
            self.text_parts.append(data)

    def handle_endtag(self, tag):
        if self.current is None:
            return

        if self.text_depth:
            self.text_depth -= 1
            if self.text_depth == 0:
                self.current["text"] = unescape(
                    "".join(self.text_parts)
                ).strip()

        if tag == "div" and self.current.get("text"):
            if self.current not in self.messages:
                self.messages.append(self.current)
                self.current = None


def main():
    request = urllib.request.Request(
        URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", errors="replace")

    parser = TelegramParser()
    parser.feed(html)

    messages = [
        message for message in parser.messages
        if message["text"]
    ][:MAX_MESSAGES]

    print(f"Canale: {CHANNEL}")
    print(f"Messaggi raccolti: {len(messages)}")
    print(json.dumps(messages, ensure_ascii=False, indent=2))

    if not messages:
        raise RuntimeError(
            "Nessun messaggio estratto: verificare accesso e parser HTML."
        )


if __name__ == "__main__":
    main()
