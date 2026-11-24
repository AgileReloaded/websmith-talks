"""Gmail argument and receipt contract. Never invokes any connector."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from delivery import gmail_arguments, gmail_receipt


class GmailContractTests(unittest.TestCase):
    def test_attachment_is_a_file_and_sender_is_the_authenticated_account(self):
        result = gmail_arguments('to@example.test', '/tmp/story.md', 'story.md', '<Author>', 'reply@example.test')
        self.assertEqual(result['attachment_files'], ['/tmp/story.md'])
        self.assertEqual(result['reply_to'], 'reply@example.test')
        self.assertNotIn('from_address', result)
        self.assertIn('&lt;Author&gt;', result['payload']['body']['content'])

    def test_actual_result_and_mcp_wrappers(self):
        value = {'id': 'synthetic-message-id', 'thread_id': 'synthetic-thread-id'}
        for result in (value, {'structuredContent': value},
                       {'content': [{'type': 'text', 'text': json.dumps(value)}]}):
            self.assertEqual(gmail_receipt(result), value)

    def test_errors_and_missing_message_id_are_never_success(self):
        for result in ({}, {'ok': True}, {'id': ''}, {'id': 'bad id'},
                       {'isError': True, 'id': 'fake-id'}, {'error': 'timeout', 'id': 'fake-id'}):
            with self.assertRaises(ValueError):
                gmail_receipt(result)
