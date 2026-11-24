"""Migration from declared synthetic TRTalks installations; no email or network."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_release import build, package
from common import atomic_json, canonical, digest, locked
import manage
import send_document


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "existing-project"
        self.previous = self.root / ".trtalks"
        self.current = self.root / ".websmith-talks"
        self.raw, self.sha = package("0.6.0a1")

    def old_installation(self, in_application=False, receipt_status="accepted"):
        """A schema-2 installation with original IDs, hashes and launcher layout."""
        manifest, files = manage.read_archive(self.raw, self.sha)
        files.pop(manage.MANIFEST)
        catalog = json.loads(json.dumps(manifest["catalog"]))
        catalog["renames"] = {"trtalks": "trstory"}
        ids = {"story": "trstory", "page": "trpage"}
        for entry in catalog["skills"]:
            entry["id"] = ids[entry["id"]]
        old_files = {}
        for name, raw in files.items():
            if name == "conversations.json":
                raw = canonical(catalog) + b"\n"
            elif name == "runtime/websmith_talks.py":
                name = "runtime/trtalks.py"
                # A runnable prior launcher for rollback verification, no delivery code.
                raw = b'import json\nfrom pathlib import Path\nprint(json.loads((Path(__file__).resolve().parents[1]/"release-manifest.json").read_text())["version"])\n'
            elif name.startswith("skills/"):
                parts = name.split("/")
                key = parts[1]
                parts[1] = ids[key]
                name = "/".join(parts)
                if name.endswith("/SKILL.md"):
                    raw = raw.replace(("name: " + key + "\n").encode(), ("name: " + ids[key] + "\n").encode())
            old_files[name] = raw
        old_manifest = {"schema": 2, "name": "trtalks", "version": "0.5.0a1", "catalog": catalog,
                        "files": {name: digest(raw) for name, raw in old_files.items()}}
        manage.validate_manifest(old_manifest, allow_trtalks=True)
        app = self.previous / "app"
        for name, raw in old_files.items():
            target = app / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            if name.startswith("skills/") and not in_application:
                target = self.root / ".agents" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
        atomic_json(app / manage.MANIFEST, old_manifest)
        atomic_json(self.previous / "install.json", {"schema": 2, "installed": True,
            "skills_in_application": in_application, "private_setting": "keep",
            "release_url": "https://github.com/AgileReloaded/TRTalks/releases/latest/download"})
        atomic_json(self.previous / "config.local.json", dict(manage.DEFAULT_CONFIG,
            sender_name="TRTalks", recipient="editor@example.test", custom_setting="keep"))
        (self.root / "trtalks").write_bytes(manage.launcher_bytes(self.root, trtalks=True))
        (self.root / "AGENTS.md").write_bytes(manage.previous_guide_bytes(in_application))
        self.draft = self.root / "drafts/example.md"
        self.draft.parent.mkdir()
        self.draft.write_text("# Documento già autorizzato\n", encoding="utf-8")
        self.request_id = "trtalks-" + "a" * 32
        self.attachment = self.previous / "deliveries" / self.request_id / self.draft.name
        self.attachment.parent.mkdir(parents=True)
        self.attachment.write_bytes(self.draft.read_bytes())
        arguments = {"name": "TRTalks", "email": "", "filename": self.draft.name, "markdown": self.draft.read_text()}
        atomic_json(self.previous / "deliveries" / (self.request_id + ".json"), {
            "schema": 3, "transport": "gmail", "request_id": self.request_id, "status": receipt_status,
            "recipient": "editor@example.test",
            "document_sha256": digest(self.draft.read_bytes()),
            "fingerprint": digest(canonical({"recipient": "editor@example.test", "arguments": arguments})),
            "attachment_path": str(self.attachment), "arguments": arguments,
            "outcome": {"gmail_accepted": True, "message_id": "synthetic-message", "request_id": self.request_id}})
        for base, content in ((app / "runtime/references/backend.local.md", b"Shared local rules"),
                              (self.previous / "overrides/trpage/references/domande.local.md", b"Local page questions"),
                              (self.previous / "backups/old-file", b"Historical backup"),
                              (self.previous / "custom/state", b"Unknown state retained")):
            base.parent.mkdir(parents=True, exist_ok=True)
            base.write_bytes(content)
        skills = app / "skills" if in_application else self.root / ".agents/skills"
        (skills / "trstory/references/rules.local.md").write_bytes(b"Local story rules")
        self.skill_root = skills

    def migrate(self, **kwargs):
        return manage.install(self.root, self.raw, self.sha, update=True, **kwargs)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*")
                if p.is_file() and p.name not in ("manage.lock", "delivery.lock")}

    def test_multi_skill_migration_preserves_data_and_accepted_receipts(self):
        self.old_installation()
        config = (self.previous / "config.local.json").read_bytes()
        receipt = (self.previous / "deliveries" / (self.request_id + ".json")).read_bytes()
        result = self.migrate()
        self.assertTrue(result["migrated_trtalks_installation"])
        self.assertEqual(result["skills"], ["page", "story"])
        self.assertFalse(self.previous.exists())
        self.assertFalse((self.root / "trtalks").exists())
        self.assertEqual((self.current / "config.local.json").read_bytes(), config)
        self.assertEqual((self.current / "deliveries" / (self.request_id + ".json")).read_bytes(), receipt)
        self.assertEqual((self.current / "deliveries" / self.request_id / self.draft.name).read_bytes(), self.draft.read_bytes())
        self.assertEqual((self.current / "overrides/page/references/domande.local.md").read_bytes(), b"Local page questions")
        self.assertFalse((self.current / "overrides/trpage").exists())
        self.assertEqual((self.current / "legacy-backups/old-file").read_bytes(), b"Historical backup")
        self.assertEqual((self.current / "custom/state").read_bytes(), b"Unknown state retained")
        self.assertEqual((self.root / ".agents/skills/story/references/rules.local.md").read_bytes(), b"Local story rules")
        self.assertEqual((self.current / "app/runtime/references/backend.local.md").read_bytes(), b"Shared local rules")
        self.assertFalse((self.root / ".agents/skills/trstory").exists())
        self.assertFalse((self.root / ".agents/skills/trpage").exists())
        self.assertEqual((self.root / "AGENTS.md").read_bytes(), manage.guide_bytes())
        settings = json.loads((self.current / "install.json").read_text())
        self.assertEqual(settings["release_url"], manage.DEFAULT_RELEASE_URL)
        self.assertEqual(settings["private_setting"], "keep")
        manage.inspect_installation(self.root)
        for operation in (lambda: send_document.retry(self.root, self.request_id),
                          lambda: send_document.send(self.root, self.draft, digest(self.draft.read_bytes()), "Authorized in test")):
            result = operation()
            self.assertTrue(result["cached"])
            self.assertEqual(result["message_id"], "synthetic-message")
        launcher = subprocess.run([sys.executable, str(self.root / "websmith-talks"), "skills"],
                                  text=True, capture_output=True, check=True)
        self.assertEqual({entry["invoke"] for entry in json.loads(launcher.stdout)["skills"]}, {"$story", "$page"})

    def test_pending_receipts_continue_to_block_duplicates_and_accept_real_result(self):
        self.old_installation(receipt_status="pending")
        self.migrate()
        with self.assertRaisesRegex(ValueError, "Tentativo già preparato"):
            send_document.send(self.root, self.draft, digest(self.draft.read_bytes()), "Authorized in test")
        receipt = self.root / "synthetic-receipt.json"
        atomic_json(receipt, {"id": "synthetic-accepted-message"})
        result = send_document.record_result(self.root, self.request_id, receipt)
        self.assertTrue(result["gmail_accepted"])
        self.assertEqual(send_document.retry(self.root, self.request_id)["message_id"], "synthetic-accepted-message")

    def test_application_mode_renames_local_rules_and_preserves_other_skills(self):
        self.old_installation(in_application=True)
        unrelated = self.root / ".agents/skills/other/SKILL.md"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_bytes(b"Independent skill")
        self.migrate()
        self.assertEqual((self.current / "app/skills/story/references/rules.local.md").read_bytes(), b"Local story rules")
        self.assertEqual((self.root / "AGENTS.md").read_bytes(), manage.guide_bytes(True))
        self.assertEqual(unrelated.read_bytes(), b"Independent skill")
        manage.inspect_installation(self.root)
        manage.uninstall(self.root)
        self.assertTrue((self.current / "config.local.json").exists())
        self.assertEqual(unrelated.read_bytes(), b"Independent skill")

    def test_conflicting_new_skill_or_overrides_stop_without_changes(self):
        self.old_installation()
        conflict = self.root / ".agents/skills/page/SKILL.md"
        conflict.parent.mkdir(parents=True)
        conflict.write_bytes(b"Unmanaged page skill")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "non appartiene"):
            self.migrate()
        self.assertEqual(self.snapshot(), before)
        conflict.unlink()
        conflict.parent.rmdir()
        override = self.previous / "overrides/page/references/domande.local.md"
        override.parent.mkdir(parents=True)
        override.write_bytes(b"Conflicting local questions")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "in conflitto"):
            self.migrate()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.current.exists())

    def test_dry_run_and_modified_source_never_change_the_old_installation(self):
        self.old_installation()
        before = self.snapshot()
        self.assertFalse(self.migrate(dry_run=True)["changed"])
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.current.exists())
        (self.skill_root / "trstory/SKILL.md").write_bytes(b"Personalized managed file")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "personalizzato"):
            self.migrate()
        self.assertEqual(self.snapshot(), before)

    def test_late_failure_restores_old_state_launcher_guide_and_skills(self):
        self.old_installation()
        before = self.snapshot()
        replace = os.replace
        def fail_old_state_removal(source, destination):
            if Path(source) == self.previous:
                raise OSError("Synthetic late migration failure")
            return replace(source, destination)
        with mock.patch("manage.os.replace", side_effect=fail_old_state_removal):
            with self.assertRaisesRegex(OSError, "Synthetic late"):
                self.migrate()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.current.exists())
        launcher = subprocess.run([sys.executable, str(self.root / "trtalks"), "--version"],
                                  text=True, capture_output=True, check=True)
        self.assertEqual(launcher.stdout.strip(), "0.5.0a1")
        self.assertTrue(self.migrate()["changed"])

    def test_unmigrated_state_cannot_be_bypassed_by_new_delivery_runtime(self):
        self.old_installation()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "da migrare"):
            send_document.send(self.root, self.draft, digest(self.draft.read_bytes()), "Authorized in test")
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.current.exists())

    def test_migration_stops_while_a_delivery_is_in_progress(self):
        self.old_installation()
        before = self.snapshot()
        with locked(self.previous / "delivery.lock"):
            with self.assertRaisesRegex(ValueError, "operazione è in corso"):
                self.migrate()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.current.exists())

    def test_custom_guide_and_disabled_delivery_preferences_are_preserved(self):
        self.old_installation()
        guide = self.root / "AGENTS.md"
        guide.write_bytes(b"Project-specific instructions")
        config = self.previous / "config.local.json"
        value = json.loads(config.read_text())
        value["send_enabled"] = False
        atomic_json(config, value)
        self.migrate()
        self.assertEqual(guide.read_bytes(), b"Project-specific instructions")
        self.assertFalse(json.loads((self.current / "config.local.json").read_text())["send_enabled"])

    def test_new_bootstrap_installs_the_renamed_package(self):
        self.bootstrap()

    def test_new_bootstrap_migrates_a_trtalks_installation(self):
        self.old_installation()
        self.bootstrap()
        self.assertFalse(self.previous.exists())
        self.assertTrue(send_document.retry(self.root, self.request_id)["cached"])

    def bootstrap(self):
        assets = Path(self.temp.name) / "assets"
        build(assets, manage.DEFAULT_RELEASE_URL)
        binaries = Path(self.temp.name) / "bin"
        binaries.mkdir()
        curl = binaries / "curl"
        curl.write_text('#!/usr/bin/env python3\n'
                        'import os, shutil, sys\nfrom pathlib import Path\n'
                        'args = sys.argv[1:]\n'
                        'asset = args[args.index("-o") - 1].rsplit("/", 1)[-1]\n'
                        'shutil.copyfile(Path(os.environ["TEST_RELEASE_ASSETS"]) / asset, args[args.index("-o") + 1])\n')
        curl.chmod(0o755)
        env = dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ["PATH"],
                   TEST_RELEASE_ASSETS=str(assets), WEBSMITH_TALKS_HOME=str(self.root))
        completed = subprocess.run(["bash", str(assets / "setup.sh")], env=env, text=True,
                                   capture_output=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue((self.root / "websmith-talks").exists())
        manifest, _, skills, _ = manage.inspect_installation(self.root)
        self.assertEqual(manifest["name"], "websmith-talks")
        self.assertEqual(set(skills), {"story", "page"})
        metadata = json.loads((assets / "release.json").read_text())
        self.assertEqual(metadata["asset"], "websmith-talks.zip")


if __name__ == "__main__":
    unittest.main()
