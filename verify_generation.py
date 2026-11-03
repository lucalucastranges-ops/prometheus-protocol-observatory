"""One bounded live AI smoke test; no Telegram call or archive mutation."""
import hashlib
from pathlib import Path
from telegram_publisher import ARCHIVE_FILE, generate_italian_summary, prepare_message


def main():
    path = Path(ARCHIVE_FILE)
    before = path.read_bytes()
    # Explicitly fictional fixture, never selected for publication.
    article = dict(title='SIMULATION: Two countries announce border security talks',
                   description='Fictional test fixture: country A and country B announced talks '
                   'on border security. No agreement has been signed. No further details are available.',
                   source='Fictional regression fixture', url='https://simulation.invalid/ai-test')
    article.update(generate_italian_summary(article))
    assert article['title_it'] and article['summary_it']
    assert isinstance(article['strategic_relevance'], str)
    assert len(prepare_message(article)) <= 4096
    assert path.read_bytes() == before
    print('PASS: live structured generation and Telegram formatting; no Telegram send; archive unchanged')
    print('Archive SHA256: ' + hashlib.sha256(before).hexdigest())


if __name__ == '__main__':
    main()
