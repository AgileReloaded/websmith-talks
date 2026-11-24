"""Real filesystem installations into isolated temporary test projects."""
import io
import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_release import package
from common import atomic_json, canonical, digest, validate_config
from catalog import required_files
import manage


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="websmith-talks-install-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "interviews"
        self.raw, self.sha = package("0.3.0a1")
        self.new, self.new_sha = package("0.3.0a2")

    def install(self):
        return manage.install(self.root, self.raw, self.sha, "https://example.test/releases/latest/download", site={"id": "example"})

    def test_application_skill_mode_preserves_protected_skill_and_supports_updates(self):
        self.install()
        protected = self.root / ".agents/skills/story/SKILL.md"
        original = protected.read_bytes()
        replace = os.replace
        def forbid_skill_mutation(source, destination):
            if ".agents" in Path(source).parts or ".agents" in Path(destination).parts:
                raise AssertionError("Protected skill mutation")
            return replace(source, destination)
        with mock.patch("manage.os.replace", side_effect=forbid_skill_mutation):
            result = manage.install(self.root, self.new, self.new_sha, update=True, skills_in_application=True)
            self.assertTrue(result["changed"])
            self.assertEqual(protected.read_bytes(), original)
            manage.inspect_installation(self.root)
            self.assertIn(".websmith-talks/app/skills/ID/", (self.root / "AGENTS.md").read_text())
            newer, sha = package("0.5.0a2")
            self.assertTrue(manage.install(self.root, newer, sha, update=True)["changed"])
            paths = subprocess.run([sys.executable, str(self.root / "websmith-talks"), "paths"],
                                   capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(paths.stdout)["skills"]["story"], str(self.root / ".websmith-talks/app/skills/story"))
            manage.uninstall(self.root)
            self.assertEqual(protected.read_bytes(), original)
            self.assertFalse((self.root / ".websmith-talks/app").exists())

    def test_installed_launcher_runs_and_refuses_overwrite(self):
        self.install()
        result = subprocess.run([sys.executable, str(self.root / "websmith-talks"), "--version"], capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "0.3.0a1"), result.stderr)
        with self.assertRaises(ValueError):
            self.install()

    def test_update_preserves_configuration_credentials_drafts_state_and_local_rules(self):
        self.install()
        local = self.root / ".websmith-talks/config.local.json"
        atomic_json(local, dict(manage.DEFAULT_CONFIG, schema=1, transport="smtp", smtp_password="synthetic-private-test-value",
                                smtp_username="local@techreloaded.it", recipient="info@techreloaded.it", site={"id": "example"}))
        before = local.read_bytes()
        draft = self.root / "drafts/intervista.md"
        draft.parent.mkdir()
        draft.write_text("Bozza da conservare")
        state = self.root / ".websmith-talks/deliveries/retained.json"
        atomic_json(state, {"id": "retained"})
        override = self.root / ".agents/skills/story/references/regole.local.md"
        override.write_text("Regole locali")
        result = manage.install(self.root, self.new, self.new_sha, update=True)
        self.assertTrue(result["changed"])
        self.assertEqual(json.loads(local.read_text()), dict(validate_config(json.loads(before)), site={"id": "example", "name": "example", "base_url": ""}))
        self.assertFalse(any("synthetic-private-test-value" in p.read_text()
                             for p in (self.root / ".websmith-talks/backups").rglob("*") if p.is_file()))
        self.assertEqual(local.stat().st_mode & 0o777, 0o600)
        self.assertEqual(draft.read_text(), "Bozza da conservare")
        self.assertEqual(json.loads(state.read_text()), {"id": "retained"})
        self.assertEqual(override.read_text(), "Regole locali")
        self.assertTrue(list((self.root / ".websmith-talks/backups").iterdir()))

    def test_modified_managed_file_stops_update(self):
        self.install()
        skill = self.root / ".agents/skills/story/SKILL.md"
        skill.write_text("Personalizzato")
        with self.assertRaises(ValueError):
            manage.install(self.root, self.new, self.new_sha, update=True)
        self.assertEqual(skill.read_text(), "Personalizzato")

    def test_failed_update_restores_previous_program(self):
        self.install()
        manifest_path = self.root / ".websmith-talks/app" / manage.MANIFEST
        before = manifest_path.read_bytes()
        actual_replace = os.replace
        def failing_replace(source, destination):
            if Path(destination) == self.root / ".websmith-talks/install.json" and Path(source).name == "metadata":
                raise OSError("synthetic state write failure")
            return actual_replace(source, destination)
        with mock.patch("manage.os.replace", side_effect=failing_replace):
            with self.assertRaises(OSError):
                manage.install(self.root, self.new, self.new_sha, update=True)
        self.assertEqual(manifest_path.read_bytes(), before)
        result = subprocess.run([sys.executable, str(self.root / "websmith-talks"), "--version"], capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "0.3.0a1")

    def test_configuration_via_installed_launcher_keeps_unknown_local_keys(self):
        self.install()
        config = self.root / ".websmith-talks/config.local.json"
        atomic_json(config, {"schema": 1, "custom_private_key": "synthetic-local-value"})
        result = subprocess.run([sys.executable, str(self.root / "websmith-talks"), "configure", "--name", "Test Name"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        current = json.loads(config.read_text())
        self.assertEqual(current["custom_private_key"], "synthetic-local-value")
        self.assertEqual(current["sender_name"], "Test Name")
        self.assertIs(current["send_enabled"], True)

    def test_bad_checksum_and_unsafe_archive_leave_no_installation(self):
        with self.assertRaises(ValueError):
            manage.install(self.root, self.raw, "0" * 64)
        self.assertFalse(self.root.exists())
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            z.writestr("websmith-talks/../../escaped.py", "bad")
        raw = buffer.getvalue()
        with self.assertRaises(ValueError):
            manage.install(self.root, raw, digest(raw))
        self.assertFalse(self.root.exists())

    def test_remote_update_download_validation_and_local_state_preservation(self):
        self.install()
        config = self.root / ".websmith-talks/config.local.json"
        before = config.read_bytes()
        def download(url, limit):
            if url.endswith("/SHA256SUMS"):
                return (self.new_sha + "  websmith-talks.zip\n").encode("ascii")
            self.assertTrue(url.endswith("/websmith-talks.zip"))
            return self.new
        with mock.patch("manage.download", side_effect=download):
            result = manage.remote_update(self.root)
        self.assertTrue(result["changed"])
        self.assertEqual(json.loads(config.read_text()), dict(validate_config(json.loads(before)), site={"id": "example", "name": "example", "base_url": ""}))

    def test_dry_run_and_downgrade_do_not_change_installation(self):
        self.install()
        target = self.root / ".websmith-talks/app"
        before = (target / manage.MANIFEST).read_bytes()
        result = manage.install(self.root, self.new, self.new_sha, update=True, dry_run=True)
        self.assertFalse(result["changed"])
        self.assertEqual((target / manage.MANIFEST).read_bytes(), before)
        manage.install(self.root, self.new, self.new_sha, update=True)
        result = manage.install(self.root, self.raw, self.sha, update=True, site={"id": "example"})
        self.assertFalse(result["changed"])
        self.assertEqual(manage.installed_manifest(target)["version"], "0.3.0a2")

    def test_uninstall_preserves_data_and_other_skills(self):
        self.install()
        other = self.root / ".agents/skills/other/SKILL.md"
        other.parent.mkdir()
        other.write_text("Other skill")
        config = (self.root / ".websmith-talks/config.local.json").read_bytes()
        manage.uninstall(self.root)
        self.assertFalse((self.root / ".agents/skills/story").exists())
        self.assertFalse((self.root / "websmith-talks").exists())
        self.assertEqual((self.root / ".websmith-talks/config.local.json").read_bytes(), config)
        self.assertEqual(other.read_text(), "Other skill")

    def test_package_is_deterministic_and_contains_no_private_files(self):
        self.assertEqual(package("0.3.0a1"), (self.raw, self.sha))
        manifest, files = manage.read_archive(self.raw, self.sha)
        self.assertEqual(set(files), required_files(manifest["catalog"]) | {manage.MANIFEST})
        self.assertFalse(any("config.local" in name or "deliveries" in name for name in files))

    def multi_skill_package(self, version="0.3.0a2"):
        source = Path(self.temp.name).resolve() / ("source-" + version)
        _, files = manage.read_archive(self.raw, self.sha)
        for name, raw in files.items():
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        catalog = json.loads((source / "conversations.json").read_text())
        catalog["skills"].append({"id": "trdemo", "display_name": "TRDemo", "description": "Fixture di test, non distribuita",
                                  "files": ["SKILL.md", "agents/openai.yaml"]})
        (source / "conversations.json").write_bytes(canonical(catalog))
        target = source / "skills/trdemo"
        (target / "agents").mkdir(parents=True)
        (target / "SKILL.md").write_text('---\nname: trdemo\ndescription: Fixture isolata per verificare più skill.\n---\n\n# TRDemo\n')
        (target / "agents/openai.yaml").write_text('interface:\n  display_name: "TRDemo"\n')
        return package(version, source=source)

    def test_multiple_skills_are_installed_listed_and_updated_together(self):
        self.install()
        raw, sha = self.multi_skill_package()
        result = manage.install(self.root, raw, sha, update=True)
        self.assertEqual(result["skills"], ["page", "story", "trdemo"])
        for key in result["skills"]:
            self.assertTrue((self.root / ".agents/skills" / key / "SKILL.md").is_file())
            self.assertFalse((self.root / ".agents/skills" / key / "scripts/send_document.py").exists())
        completed = subprocess.run([sys.executable, str(self.root / "websmith-talks"), "skills"], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual({s["invoke"] for s in json.loads(completed.stdout)["skills"]}, {"$story", "$page", "$trdemo"})
        paths = subprocess.run([sys.executable, str(self.root / "websmith-talks"), "paths"], capture_output=True, text=True)
        self.assertEqual(json.loads(paths.stdout)["runtime"], str(self.root / ".websmith-talks/app/runtime"))

    def test_update_adds_page_to_story_only_installation_and_preserves_local_data(self):
        source = Path(self.temp.name) / "story-only-source"
        _, files = manage.read_archive(self.raw, self.sha)
        for name, raw in files.items():
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        catalog_path = source / "conversations.json"
        catalog = json.loads(catalog_path.read_text())
        catalog["skills"] = [s for s in catalog["skills"] if s["id"] != "page"]
        catalog["renames"] = {k: v for k, v in catalog["renames"].items() if v != "page"}
        catalog_path.write_bytes(canonical(catalog))
        raw, sha = package("0.3.0a1", source=source)
        manage.install(self.root, raw, sha, site={"id": "example"})
        self.assertFalse((self.root / ".agents/skills/page").exists())
        config = self.root / ".websmith-talks/config.local.json"
        before = config.read_bytes()
        draft = self.root / "drafts/pagina-esistente.md"
        draft.parent.mkdir()
        draft.write_text("Documento da conservare")
        override = self.root / ".websmith-talks/overrides/page/references/domande.local.md"
        override.parent.mkdir(parents=True)
        override.write_text("Domande locali da conservare")

        result = manage.install(self.root, self.new, self.new_sha, update=True)

        self.assertEqual(result["skills"], ["page", "story"])
        current_catalog = json.loads((ROOT / "conversations.json").read_text())
        entry = next(s for s in current_catalog["skills"] if s["id"] == "page")
        for name in entry["files"]:
            self.assertEqual((self.root / ".agents/skills/page" / name).read_bytes(),
                             (ROOT / "skills/page" / name).read_bytes())
        self.assertEqual(config.read_bytes(), before)
        self.assertEqual(draft.read_text(), "Documento da conservare")
        self.assertEqual(override.read_text(), "Domande locali da conservare")
        completed = subprocess.run([sys.executable, str(self.root / "websmith-talks"), "skills"],
                                   capture_output=True, text=True, check=True)
        self.assertEqual({s["invoke"] for s in json.loads(completed.stdout)["skills"]},
                         {"$story", "$page"})

    def test_new_skill_conflict_stops_entire_update(self):
        self.install()
        target = self.root / ".agents/skills/trdemo/SKILL.md"
        target.parent.mkdir()
        target.write_text("Skill indipendente")
        raw, sha = self.multi_skill_package()
        with self.assertRaises(ValueError):
            manage.install(self.root, raw, sha, update=True)
        self.assertEqual(target.read_text(), "Skill indipendente")
        self.assertEqual(manage.installed_manifest(self.root / ".websmith-talks/app")["version"], "0.3.0a1")

    def test_removed_managed_skill_is_backed_up_with_its_local_rules(self):
        self.install()
        raw, sha = self.multi_skill_package()
        manage.install(self.root, raw, sha, update=True)
        local = self.root / ".agents/skills/trdemo/demo.local.md"
        local.write_text("Da conservare")
        raw, sha = package("0.3.0a3")
        manage.install(self.root, raw, sha, update=True)
        self.assertFalse(local.parent.exists())
        backups = list((self.root / ".websmith-talks/backups").rglob("demo.local.md"))
        self.assertTrue(any(p.read_text() == "Da conservare" for p in backups))

    def test_existing_project_instructions_are_never_overwritten_or_deleted(self):
        self.root.mkdir(parents=True)
        guide = self.root / "AGENTS.md"
        guide.write_text("Istruzioni specifiche del progetto")
        self.install()
        manage.install(self.root, self.new, self.new_sha, update=True)
        manage.uninstall(self.root)
        self.assertEqual(guide.read_text(), "Istruzioni specifiche del progetto")

    def test_migrate_legacy_single_skill_preserves_state_and_moves_local_overrides(self):
        legacy = self.root / ".agents/skills/trtalks"
        hashes = {}
        for name in manage.LEGACY_REQUIRED:
            target = legacy / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"Legacy fixture; never executed\n")
            hashes[name] = digest(target.read_bytes())
        atomic_json(legacy / manage.MANIFEST, {"schema": 1, "name": "trtalks", "version": "0.2.0a1", "files": hashes})
        (legacy / "references/regole.local.md").write_text("Regole del caso")
        (legacy / "references/backend.local.md").write_text("Regole condivise")
        config = self.root / ".trtalks/config.local.json"
        atomic_json(config, {"schema": 1, "send_enabled": False, "private_setting": "fixture"})
        atomic_json(self.root / ".trtalks/install.json", {"schema": 1, "installed": True, "release_url": "https://example.test/releases"})
        retained = self.root / ".trtalks/deliveries/retained.json"
        atomic_json(retained, {"request_id": "retained-original-id"})
        before = config.read_bytes()
        (self.root / "trtalks").write_bytes(manage.launcher_bytes(self.root, legacy=True))
        result = manage.install(self.root, self.raw, self.sha, update=True, site={"id": "example"})
        self.assertTrue(result["migrated_legacy_installation"])
        self.assertFalse(legacy.exists())
        self.assertEqual((self.root / ".agents/skills/story/references/regole.local.md").read_text(), "Regole del caso")
        self.assertEqual((self.root / ".websmith-talks/app/runtime/references/backend.local.md").read_text(), "Regole condivise")
        self.assertEqual(json.loads((self.root / ".websmith-talks/config.local.json").read_text()), dict(validate_config(json.loads(before)), site={"id": "example", "name": "example", "base_url": ""}))
        self.assertEqual(json.loads((self.root / ".websmith-talks/deliveries/retained.json").read_text())["request_id"], "retained-original-id")


if __name__ == "__main__":
    unittest.main()
