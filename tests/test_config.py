"""Gmail preferences, removal of legacy credentials and obsolete CLI options."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from common import DEFAULT_CONFIG, atomic_json, load_config
import trtalks


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / '.trtalks/config.local.json'

    def configure(self, *args):
        with redirect_stdout(io.StringIO()):
            return trtalks.main(['--root', str(self.root), 'configure', *args])

    def test_defaults_need_no_connection_credentials(self):
        self.assertEqual(self.configure(), 0)
        current = load_config(self.root)
        self.assertEqual(current['transport'], 'gmail')
        self.assertTrue(current['send_enabled'])
        self.assertFalse(any(k.startswith('smtp_') for k in current))
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_migrate_without_losing_destination_preferences_or_custom_settings(self):
        atomic_json(self.path, {'schema': 1, 'transport': 'smtp', 'smtp_password': 'synthetic-secret',
                               'smtp_host': 'old.test', 'endpoint': 'https://old.test',
                               'recipient': 'editor@example.test', 'sender_name': 'Prova',
                               'send_enabled': False, 'custom_setting': 'keep'})
        self.assertEqual(self.configure('--email', 'reply@example.test'), 0)
        current = json.loads(self.path.read_text())
        self.assertEqual(current['recipient'], 'editor@example.test')
        self.assertFalse(current['send_enabled'])
        self.assertEqual(current['custom_setting'], 'keep')
        self.assertEqual(current['reply_to'], 'reply@example.test')
        self.assertEqual(current['schema'], 2)
        self.assertNotIn('synthetic-secret', self.path.read_text())
        self.assertNotIn('endpoint', current)
        self.assertFalse(any(k.startswith('smtp_') for k in current))

    def test_invalid_preferences_do_not_change_file(self):
        atomic_json(self.path, DEFAULT_CONFIG)
        before = self.path.read_bytes()
        for args in (['--recipient', 'bad\r\nBcc: person@example.test'], ['--name', 'bad\nheader']):
            self.assertEqual(self.configure(*args), 1)
            self.assertEqual(self.path.read_bytes(), before)

    def test_init_and_connection_flags_removed(self):
        for args in (['init'], ['configure', '--smtp-host', 'old.test'], ['configure', '--smtp-password']):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                trtalks.main(['--root', str(self.root), *args])
            self.assertEqual(error.exception.code, 2)
        self.assertFalse(self.path.exists())
