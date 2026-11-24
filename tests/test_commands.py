"""Real install/update commands in isolated projects, without network or email."""
import json
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_release import package
import manage
import websmith_talks


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve()
        self.project = self.directory / "site-project"
        self.project.mkdir()
        self.source = self.directory / "source"
        self.source.mkdir()
        for name in ("runtime", "scripts", "skills", "docs"):
            shutil.copytree(ROOT / name, self.source / name, ignore=shutil.ignore_patterns("__pycache__"))
        for name in ("VERSION", "conversations.json", "setup.sh"):
            shutil.copy2(ROOT / name, self.source / name)
        (self.source / "VERSION").write_text("0.8.0a1\n")
        self.binary = self.directory / "bin"
        result = manage.register_command(self.source / "runtime/websmith_talks.py", self.binary)
        self.command = Path(result["command_path"])

    def run_command(self, *arguments, cwd=None, check=True):
        result = subprocess.run([str(self.command), *map(str, arguments)], cwd=cwd or self.project,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), text=True, capture_output=True, timeout=30)
        if check:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(result.stdout)
        return result

    def install(self):
        return self.run_command("install", "--source", self.source, "--site-id", "example", "--recipient", "editor@example.test")

    def test_install_and_update_from_subdirectory_preserve_preferences_and_documents(self):
        self.assertTrue(self.install()["changed"])
        config = self.project / ".websmith-talks/config.local.json"
        before = config.read_bytes()
        draft = self.project / "drafts/existing.md"
        draft.parent.mkdir()
        draft.write_bytes(b"Existing draft")
        receipt = self.project / ".websmith-talks/deliveries/retained.json"
        receipt.parent.mkdir()
        receipt.write_bytes(b'{"synthetic":"retained"}\n')
        (self.source / "VERSION").write_text("0.8.0a2\n")
        preview = self.run_command("update", "--source", self.source, "--dry-run", cwd=draft.parent)
        self.assertEqual(preview["would_install"], "0.8.0a2")
        self.assertEqual(manage.installed_manifest(self.project / ".websmith-talks/app")["version"], "0.8.0a1")
        updated = self.run_command("update", "--source", self.source, cwd=draft.parent)
        self.assertEqual(updated["version"], "0.8.0a2")
        self.assertEqual(config.read_bytes(), before)
        self.assertEqual(draft.read_bytes(), b"Existing draft")
        self.assertEqual(receipt.read_bytes(), b'{"synthetic":"retained"}\n')
        metadata = json.loads((self.project / ".websmith-talks/install.json").read_text())
        self.assertEqual(metadata["source_root"], str(self.source))

    def test_source_update_accepts_new_source_bytes_at_the_same_development_version(self):
        self.install()
        file = self.source / "runtime/references/backend.md"
        file.write_text(file.read_text() + "\nUpdated local development instructions.\n")
        result = self.run_command("update", "--source", self.source)
        self.assertTrue(result["changed"])
        self.assertEqual((self.project / ".websmith-talks/app/runtime/references/backend.md").read_bytes(), file.read_bytes())
        self.assertFalse(self.run_command("update", "--source", self.source)["changed"])

    def test_global_command_keeps_separate_projects_and_honors_explicit_root(self):
        self.install()
        other = self.directory / "other-project"
        other.mkdir()
        result = self.run_command("install", "--source", self.source, "--site-id", "other", cwd=other)
        self.assertEqual(result["site"]["id"], "other")
        self.assertEqual(self.run_command("status", cwd=other)["site"]["id"], "other")
        self.assertEqual(self.run_command("status", "--root", self.project, cwd=other)["site"]["id"], "example")

    def test_existing_custom_command_is_never_overwritten(self):
        self.command.write_bytes(b"#!/bin/sh\necho custom\n")
        with self.assertRaisesRegex(ValueError, "personalizzato"):
            manage.register_command(self.source / "runtime/websmith_talks.py", self.binary)
        self.assertEqual(self.command.read_bytes(), b"#!/bin/sh\necho custom\n")

    def test_registered_command_can_be_repointed_only_if_unmodified(self):
        original = self.command.read_bytes()
        manage.register_command(self.source / "runtime/websmith_talks.py", self.binary)
        self.assertEqual(self.command.read_bytes(), original)
        self.install()
        manage.register_command(self.project / ".websmith-talks/app/runtime/websmith_talks.py", self.binary)
        self.assertNotEqual(self.command.read_bytes(), original)
        self.assertEqual(self.run_command("status")["site"]["id"], "example")

    def test_release_install_verifies_download_and_retains_release_update_mode(self):
        raw, checksum = package("0.8.0a1")
        def download(url, limit):
            self.assertTrue(url.startswith(manage.DEFAULT_RELEASE_URL + "/"))
            return (checksum + "  websmith-talks.zip\n").encode() if url.endswith("SHA256SUMS") else raw
        with mock.patch("manage.download", side_effect=download):
            result = manage.remote_install(self.project, site={"id": "example"})
        self.assertTrue(result["changed"])
        metadata = json.loads((self.project / ".websmith-talks/install.json").read_text())
        self.assertNotIn("source_root", metadata)
        self.assertEqual(metadata["release_url"], manage.DEFAULT_RELEASE_URL)

    def test_install_in_existing_project_requires_update_and_never_changes_the_site(self):
        self.install()
        config = self.project / ".websmith-talks/config.local.json"
        before = config.read_bytes()
        self.assertNotEqual(self.run_command("install", "--source", self.source, "--site-id", "other", check=False).returncode, 0)
        self.assertEqual(config.read_bytes(), before)

    def test_install_help_explains_site_and_source_options_without_installing(self):
        result = self.run_command("install", "--help", check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--site-id", result.stdout)
        self.assertIn("--source", result.stdout)
        self.assertFalse((self.project / ".websmith-talks").exists())

    def test_explicit_update_mode_switch_is_saved_even_at_the_same_version(self):
        self.install()
        raw, checksum = package("0.8.0a1")
        def download(url, limit):
            return (checksum + "  websmith-talks.zip\n").encode() if url.endswith("SHA256SUMS") else raw
        with mock.patch("manage.download", side_effect=download):
            manage.remote_update(self.project, manage.DEFAULT_RELEASE_URL)
        path = self.project / ".websmith-talks/install.json"
        self.assertNotIn("source_root", json.loads(path.read_text()))
        manage.source_install(self.project, self.source, update=True)
        self.assertEqual(json.loads(path.read_text())["source_root"], str(self.source))

    def release_download(self, version):
        raw, checksum = package(version)
        def download(url, limit):
            self.assertTrue(url.startswith(manage.DEFAULT_RELEASE_URL + "/"))
            return (checksum + "  websmith-talks.zip\n").encode() if url.endswith("SHA256SUMS") else raw
        return download

    def test_plain_install_uses_github_release_even_when_running_from_checkout(self):
        output = io.StringIO()
        with mock.patch("websmith_talks.APPLICATION", self.source), \
             mock.patch("manage.download", side_effect=self.release_download("0.8.0a1")) as download, \
             mock.patch("manage.source_install", side_effect=AssertionError("Implicit local source")) as local, \
             redirect_stdout(output):
            self.assertEqual(websmith_talks.main(["--root", str(self.project), "install", "--site-id", "example"]), 0)
        self.assertEqual(download.call_count, 2)
        local.assert_not_called()
        metadata = json.loads((self.project / ".websmith-talks/install.json").read_text())
        self.assertNotIn("source_root", metadata)

    def test_plain_update_uses_release_even_for_a_previous_local_installation(self):
        self.install()
        (self.source / "VERSION").write_text("99.0.0\n")
        config = (self.project / ".websmith-talks/config.local.json").read_bytes()
        output = io.StringIO()
        with mock.patch("websmith_talks.APPLICATION", self.source), \
             mock.patch("manage.download", side_effect=self.release_download("0.8.0a2")) as download, \
             mock.patch("manage.source_install", side_effect=AssertionError("Implicit local source")) as local, \
             redirect_stdout(output):
            self.assertEqual(websmith_talks.main(["--root", str(self.project), "update"]), 0)
        self.assertEqual(json.loads(output.getvalue())["version"], "0.8.0a2")
        self.assertEqual(download.call_count, 2)
        local.assert_not_called()
        self.assertEqual((self.project / ".websmith-talks/config.local.json").read_bytes(), config)
        self.assertNotIn("source_root", json.loads((self.project / ".websmith-talks/install.json").read_text()))

    def test_release_failure_never_falls_back_to_local_sources(self):
        self.install()
        before = (self.project / ".websmith-talks/app/release-manifest.json").read_bytes()
        with mock.patch("manage.download", side_effect=OSError("Synthetic GitHub failure")), \
             mock.patch("manage.source_install", side_effect=AssertionError("Local fallback")) as local, \
             redirect_stdout(io.StringIO()):
            self.assertEqual(websmith_talks.main(["--root", str(self.project), "update"]), 1)
        local.assert_not_called()
        self.assertEqual((self.project / ".websmith-talks/app/release-manifest.json").read_bytes(), before)

    def test_old_generated_launcher_is_upgraded_but_custom_changes_are_preserved(self):
        fallback = self.source / "runtime/websmith_talks.py"
        self.command.write_bytes(manage.command_bytes(fallback, legacy=True))
        manage.register_command(fallback, self.binary)
        self.assertEqual(self.command.read_bytes(), manage.command_bytes(fallback))
        custom = manage.command_bytes(fallback, legacy=True) + b"\n# Custom changes\n"
        self.command.write_bytes(custom)
        with self.assertRaisesRegex(ValueError, "personalizzato"):
            manage.register_command(fallback, self.binary)
        self.assertEqual(self.command.read_bytes(), custom)


if __name__ == "__main__":
    unittest.main()
