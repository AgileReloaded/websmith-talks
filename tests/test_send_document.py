"""Authorization and Gmail lifecycle using isolated files and synthetic receipts."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from common import DEFAULT_CONFIG, atomic_json, digest
import send_document as delivery


class GmailDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.config = self.root / '.trtalks/config.local.json'
        atomic_json(self.config, DEFAULT_CONFIG)
        self.draft = self.root / 'story.md'
        self.raw = '# Resoconto\r\n\r\nCittà, attività e risultati.\r\n'.encode('utf-8')
        self.draft.write_bytes(self.raw)
        self.sha = digest(self.raw)
        # All operations below must work with network sockets prohibited.
        self.socket = patch('socket.socket', side_effect=AssertionError('Unexpected network connection'))
        self.socket.start()
        self.addCleanup(self.socket.stop)

    def prepare(self):
        return delivery.send(self.root, self.draft, self.sha, 'Autorizzazione sintetica per questo test isolato')

    def receipt(self, result, value):
        file = self.root / 'connector-response.json'
        atomic_json(file, value)
        return delivery.record_result(self.root, result['request_id'], file)

    def test_prepare_preserves_exact_bytes_without_claiming_email_was_sent(self):
        result = self.prepare()
        self.assertFalse(result['email_sent'])
        self.assertEqual(result['local_status'], 'pending')
        args = result['tool_arguments']
        self.assertEqual(Path(args['attachment_files'][0]).read_bytes(), self.raw)
        self.draft.write_text('Later edits')
        self.assertEqual(Path(args['attachment_files'][0]).read_bytes(), self.raw)
        self.assertEqual(args['to'], DEFAULT_CONFIG['recipient'])

    def test_missing_authorization_changed_bytes_disabled_send(self):
        for sha, auth in (('0' * 64, 'yes'), (self.sha, ''), (self.sha, ' ')):
            with self.assertRaises(ValueError):
                delivery.send(self.root, self.draft, sha, auth)
        atomic_json(self.config, dict(DEFAULT_CONFIG, send_enabled=False))
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertFalse((self.root / '.trtalks/deliveries').exists())

    def test_pending_and_uncertain_block_duplicate_and_retry(self):
        result = self.prepare()
        for _ in range(2):
            with self.assertRaises(ValueError):
                self.prepare()
            with self.assertRaises(ValueError):
                delivery.retry(self.root, result['request_id'])
            self.assertEqual(self.receipt(result, {'isError': True, 'error': 'Synthetic timeout'})['local_status'], 'uncertain')

    def test_real_message_id_confirms_and_then_reuses_receipt(self):
        result = self.prepare()
        receipt = self.receipt(result, {'id': 'synthetic-message-id', 'thread_id': 'synthetic-thread-id'})
        self.assertTrue(receipt['gmail_accepted'])
        self.assertEqual(receipt['message_id'], 'synthetic-message-id')
        self.assertEqual(receipt['email_delivery'], 'unconfirmed')
        self.assertTrue(self.prepare()['cached'])
        self.assertTrue(delivery.retry(self.root, result['request_id'])['cached'])
        self.assertNotIn('tool_arguments', self.prepare())

    def test_missing_id_never_confirms_delivery(self):
        result = self.prepare()
        receipt = self.receipt(result, {'ok': True})
        self.assertFalse(receipt['gmail_accepted'])
        self.assertEqual(receipt['local_status'], 'uncertain')

    def test_changed_recipient_does_not_bypass_duplicate_protection(self):
        self.prepare()
        atomic_json(self.config, dict(DEFAULT_CONFIG, recipient='other@example.test'))
        with self.assertRaises(ValueError):
            self.prepare()

    def test_old_attempt_preserved_and_not_retried(self):
        request = 'trtalks-' + 'a' * 32
        path = self.root / '.trtalks/deliveries' / (request + '.json')
        original = {'transport': 'smtp', 'status': 'failed_safe', 'document_sha256': self.sha}
        atomic_json(path, original)
        with self.assertRaises(ValueError):
            self.prepare()
        with self.assertRaises(ValueError):
            delivery.retry(self.root, request)
        self.assertEqual(json.loads(path.read_text()), original)

    def test_write_failure_blocks_tool_call(self):
        with patch('send_document.atomic_json', side_effect=OSError('Synthetic disk failure')):
            with self.assertRaises(OSError):
                self.prepare()

    def test_status_and_dry_run_are_honest_about_connection(self):
        result = delivery.status(self.root)
        self.assertFalse(result['network_called'])
        self.assertFalse(result['gmail_connection_verified'])
        self.assertEqual(delivery.dry_run(self.root, self.draft)['sha256'], self.sha)
        self.assertTrue(Path(delivery.probe(self.root)['draft_path']).is_file())
