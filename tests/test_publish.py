"""Publisher preflight tests with declared local fixtures; no GitHub mutations."""
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import publish


class PublishTests(unittest.TestCase):
    def test_invalid_repository_is_rejected_before_commands(self):
        with mock.patch("publish.command") as command:
            with self.assertRaises(ValueError):
                publish.publish("https://github.com/owner/repo")
            command.assert_not_called()

    def test_dry_run_never_uses_git_or_github(self):
        with mock.patch("publish.build", return_value={"version": "0.3.0a1"}), mock.patch("publish.command") as command:
            result = publish.publish("AgileReloaded/TRTalks", dry_run=True)
            self.assertFalse(result["published"])
            self.assertIn("releases/latest/download/setup.sh", result["install_command_after_publication"])
            command.assert_not_called()

    def test_network_failure_is_not_treated_as_missing_repository(self):
        def command(args, check=True):
            if args[:3] == ["gh", "auth", "status"]:
                return subprocess.CompletedProcess(args, 0, "", "")
            return subprocess.CompletedProcess(args, 1, "", "Synthetic network failure")
        with mock.patch("publish.build", return_value={"version": "0.3.0a1"}), mock.patch("publish.command", side_effect=command) as observed:
            with self.assertRaisesRegex(RuntimeError, "Synthetic network failure"):
                publish.publish("AgileReloaded/TRTalks")
            self.assertEqual(len(observed.call_args_list), 2)
            self.assertTrue(all(call.args[0][0] == "gh" for call in observed.call_args_list))


if __name__ == "__main__":
    unittest.main()
