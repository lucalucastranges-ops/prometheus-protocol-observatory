"""Offline regression replay: no credentials, network, Telegram or archive writes."""
import hashlib
from pathlib import Path
from unittest.mock import patch
import telegram_publisher as publisher


def main():
    archive = Path(publisher.ARCHIVE_FILE)
    before = archive.read_bytes() if archive.exists() else None
    known = publisher.load_archive()
    candidates = ([dict(known[0], description='Already published')] if known else [])
    candidates += [dict(title=f'Simulation {i}', description='Documented military conflict.',
                        source=f'Source {i % 3}', url=f'https://simulation.invalid/{i}') for i in range(6)]
    generated = dict(title_it='Titolo italiano', summary_it='Fatti documentati.',
                     strategic_relevance='La fonte consente soltanto inferenze caute.')
    with patch.object(publisher, 'DRY_RUN', True), patch.object(
            publisher, 'generate_italian_summary', side_effect=[ValueError('truncated AI JSON'),
                                                              generated, generated, generated]), patch.object(
            publisher, 'send_telegram_message', side_effect=AssertionError('Telegram forbidden')) as send, patch.object(
            publisher.urllib.request, 'urlopen', side_effect=AssertionError('Network forbidden')), patch(
            'builtins.open', side_effect=AssertionError('Archive writes forbidden')):
        # Load the already-read real archive without opening it in the guarded block.
        with patch.object(publisher, 'load_archive', return_value=known), patch.object(publisher, 'load_state', return_value={}):
            assert publisher.publish_new_articles(candidates) == 3
        send.assert_not_called()
    after = archive.read_bytes() if archive.exists() else None
    assert before == after, 'Archive changed'
    print('PASS: 3 simulated publications after AI failure; no Telegram/network; archive unchanged')
    if before is not None:
        print('Archive SHA256: ' + hashlib.sha256(before).hexdigest())


if __name__ == '__main__':
    main()
