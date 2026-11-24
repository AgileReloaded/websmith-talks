"""One site per installation, exact email routing and conservative updates."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_release import package
from common import atomic_json, digest, load_config, site_tag, validate_site
import manage
import send_document
import websmith_talks


class SiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "talks"
        self.site = {"id": "example", "name": "Example site", "base_url": "https://example.test"}
        self.raw, self.sha = package("0.7.0a1")

    def install(self, **kwargs):
        return manage.install(self.root, self.raw, self.sha, site=self.site,
                              recipient="editor@example.test", **kwargs)

    def configure(self, *args):
        with redirect_stdout(io.StringIO()):
            return websmith_talks.main(["--root", str(self.root), "configure", *args])

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*")
                if p.is_file() and p.name not in ("manage.lock", "delivery.lock")}

    def test_setup_requires_explicit_valid_site_before_creating_an_installation(self):
        with self.assertRaisesRegex(ValueError, "Sito non configurato"):
            manage.install(self.root, self.raw, self.sha)
        self.assertFalse(self.root.exists())
        for key in ("", "Example", "example.test", "../example", "x] [websmith:other", "x\r\nBcc"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                manage.install(self.root, self.raw, self.sha, site={"id": key})
            self.assertFalse(self.root.exists())
        self.install()
        self.assertEqual(load_config(self.root)["site"], self.site)
        self.assertEqual(json.loads((self.root / ".websmith-talks/install.json").read_text())["site"], self.site)

    def test_websmith_identifiers_are_preserved_without_slugging_or_normalizing(self):
        for key in ("example", "example-2", "2example", "example--"):
            self.assertEqual(validate_site({"id": key})["id"], key)
            self.assertEqual(site_tag({"id": key}), "[websmith:" + key + "]")
        for url in ("ftp://example.test", "https://user:pass@example.test", "https://example.test?q=x", "https://example.test/#x"):
            with self.assertRaises(ValueError):
                validate_site({"id": "example", "base_url": url})

    def test_configure_and_setup_cannot_change_the_site(self):
        self.install()
        before = self.snapshot()
        self.assertEqual(self.configure("--site-id", "other"), 1)
        with self.assertRaisesRegex(ValueError, "già associata"):
            manage.install(self.root, self.raw, self.sha, update=True, site={"id": "other"})
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.install(update=True)["changed"])
        self.assertEqual(self.configure("--site-name", "Updated title"), 0)
        self.assertEqual(load_config(self.root)["site"]["id"], "example")
        self.assertEqual(load_config(self.root)["site"]["name"], "Updated title")

    def test_updates_preserve_binding_and_detect_a_config_edited_to_another_site(self):
        self.install()
        raw, sha = package("0.7.0a2")
        manage.install(self.root, raw, sha, update=True)
        self.assertEqual(load_config(self.root)["site"], self.site)
        path = self.root / ".websmith-talks/config.local.json"
        config = json.loads(path.read_text())
        config["site"] = {"id": "other"}
        atomic_json(path, config)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "differisce"):
            load_config(self.root)
        self.assertEqual(self.configure("--site-id", "other"), 1)
        self.assertEqual(self.snapshot(), before)

    def test_an_unbound_previous_installation_requires_binding_and_keeps_documents(self):
        self.install()
        state = self.root / ".websmith-talks"
        for name in ("install.json", "config.local.json"):
            value = json.loads((state / name).read_text())
            value.pop("site", None)
            atomic_json(state / name, value)
        draft = self.root / "drafts/previous.md"
        draft.parent.mkdir()
        draft.write_bytes(b"Previous draft")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "Sito non configurato"):
            manage.install(self.root, self.raw, self.sha, update=True)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.configure("--site-id", "example"), 0)
        self.assertEqual(draft.read_bytes(), b"Previous draft")
        self.assertEqual(send_document.status(self.root)["email_tag"], "[websmith:example]")

    def test_configure_rolls_back_both_binding_files_on_metadata_failure(self):
        self.install()
        before = self.snapshot()
        replace = manage.os.replace
        def fail(source, target):
            if Path(source).name == "metadata":
                raise OSError("Synthetic metadata failure")
            return replace(source, target)
        with mock.patch("manage.os.replace", side_effect=fail):
            self.assertEqual(self.configure("--site-name", "Different title"), 1)
        self.assertEqual(self.snapshot(), before)

    def test_shared_mailbox_receives_different_tags_for_separate_installations(self):
        subjects = []
        for key in ("example", "other"):
            project = self.root.parent / key
            manage.install(project, self.raw, self.sha, site={"id": key}, recipient="shared@example.test")
            file = project / "same.md"
            file.write_bytes(b"# Same bytes in separate sites\n")
            result = send_document.send(project, file, digest(file.read_bytes()), "Synthetic authorization")
            arguments = result["tool_arguments"]
            subjects.append(arguments["subject"])
            self.assertEqual(arguments["to"], "shared@example.test")
            self.assertEqual(arguments["subject"].count("[websmith:"), 1)
            self.assertTrue(arguments["subject"].startswith("[websmith:" + key + "] "))
            record = json.loads(Path(result["state_file"]).read_text())
            self.assertEqual(record["site_id"], key)
            self.assertEqual(send_document.dry_run(project, file)["subject"], arguments["subject"])
            self.assertEqual(Path(arguments["attachment_files"][0]).read_bytes(), file.read_bytes())
        self.assertNotEqual(*subjects)

    def test_missing_site_never_creates_a_delivery_attempt(self):
        self.root.mkdir()
        atomic_json(self.root / ".websmith-talks/config.local.json", {"schema": 2, "recipient": "editor@example.test"})
        file = self.root / "draft.md"
        file.write_bytes(b"# Draft\n")
        self.assertFalse(send_document.status(self.root)["site_configured"])
        with self.assertRaisesRegex(ValueError, "Sito non configurato"):
            send_document.send(self.root, file, digest(file.read_bytes()), "Synthetic authorization")
        self.assertFalse((self.root / ".websmith-talks/deliveries").exists())

    def test_receipts_from_another_site_cannot_be_reused_or_modified(self):
        self.install()
        file = self.root / "draft.md"
        file.write_bytes(b"# A site-bound delivery\n")
        result = send_document.send(self.root, file, digest(file.read_bytes()), "Synthetic authorization")
        path = Path(result["state_file"])
        record = json.loads(path.read_text())
        record["site_id"] = "other"
        atomic_json(path, record)
        before = path.read_bytes()
        for operation in (
            lambda: send_document.retry(self.root, result["request_id"]),
            lambda: send_document.record_result(self.root, result["request_id"], self.root / "unused-receipt.json"),
            lambda: send_document.send(self.root, file, digest(file.read_bytes()), "Synthetic authorization"),
        ):
            with self.assertRaisesRegex(ValueError, "altro sito"):
                operation()
        self.assertEqual(path.read_bytes(), before)

    def test_interactive_setup_reads_site_from_terminal_and_does_not_ask_on_upgrade(self):
        archive = self.root.parent / "package.zip"
        archive.write_bytes(self.raw)
        arguments = ["install", "--root", str(self.root), "--archive", str(archive),
                     "--sha256", self.sha, "--interactive", "--upgrade"]
        with mock.patch("manage.open", create=True, side_effect=[io.StringIO("example\nExample website\n"), io.StringIO()]), redirect_stdout(io.StringIO()):
            self.assertEqual(manage.main(arguments), 0)
        self.assertEqual(load_config(self.root)["site"]["id"], "example")
        self.assertEqual(load_config(self.root)["site"]["name"], "Example website")
        with mock.patch("manage.open", create=True) as terminal, redirect_stdout(io.StringIO()):
            self.assertEqual(manage.main(arguments), 0)
            terminal.assert_not_called()

    def test_each_question_is_visible_before_the_installer_waits_for_its_answer(self):
        archive = self.root.parent / "package.zip"
        archive.write_bytes(self.raw)
        arguments = ["install", "--root", str(self.root), "--archive", str(archive),
                     "--sha256", self.sha, "--interactive"]
        terminal_output = io.BytesIO()
        writer = io.TextIOWrapper(terminal_output, encoding="utf-8", line_buffering=True)
        reader = mock.MagicMock()
        reader.__enter__.return_value = reader
        exchanges = iter([
            ("Identificativo del sito da usare (site.id di Websmith): ", "example\n"),
            ("Nome del sito [example]: ", "Example website\n"),
        ])
        def answer_only_after_visible_question():
            question, answer = next(exchanges)
            self.assertTrue(terminal_output.getvalue().decode("utf-8").endswith(question),
                            "Installer waits for input before displaying the question")
            return answer
        reader.readline.side_effect = answer_only_after_visible_question
        with mock.patch("manage.open", create=True, side_effect=[reader, writer]), redirect_stdout(io.StringIO()):
            self.assertEqual(manage.main(arguments), 0)
        self.assertEqual(load_config(self.root)["site"]["name"], "Example website")

    def test_interactive_setup_asks_for_name_even_when_id_is_already_supplied(self):
        archive = self.root.parent / "package.zip"
        archive.write_bytes(self.raw)
        arguments = ["install", "--root", str(self.root), "--archive", str(archive),
                     "--sha256", self.sha, "--interactive", "--site-id", "example"]
        with mock.patch("manage.open", create=True, side_effect=[io.StringIO("Named website\n"), io.StringIO()]), redirect_stdout(io.StringIO()):
            self.assertEqual(manage.main(arguments), 0)
        self.assertEqual(load_config(self.root)["site"]["name"], "Named website")

    def test_interactive_setup_accepts_default_name_on_enter(self):
        archive = self.root.parent / "package.zip"
        archive.write_bytes(self.raw)
        arguments = ["install", "--root", str(self.root), "--archive", str(archive),
                     "--sha256", self.sha, "--interactive"]
        with mock.patch("manage.open", create=True, side_effect=[io.StringIO("example\n\n"), io.StringIO()]), redirect_stdout(io.StringIO()):
            self.assertEqual(manage.main(arguments), 0)
        self.assertEqual(load_config(self.root)["site"]["name"], "example")

    def test_interrupted_name_prompt_does_not_create_an_installation(self):
        archive = self.root.parent / "package.zip"
        archive.write_bytes(self.raw)
        arguments = ["install", "--root", str(self.root), "--archive", str(archive),
                     "--sha256", self.sha, "--interactive"]
        with mock.patch("manage.open", create=True, side_effect=[io.StringIO("example\n"), io.StringIO()]), redirect_stdout(io.StringIO()):
            self.assertEqual(manage.main(arguments), 1)
        self.assertFalse(self.root.exists())

    def test_noninteractive_setup_with_explicit_id_uses_it_as_default_name(self):
        archive = self.root.parent / "package.zip"
        archive.write_bytes(self.raw)
        arguments = ["install", "--root", str(self.root), "--archive", str(archive),
                     "--sha256", self.sha, "--interactive", "--site-id", "example"]
        with mock.patch("manage.open", create=True, side_effect=OSError("No terminal")), redirect_stdout(io.StringIO()):
            self.assertEqual(manage.main(arguments), 0)
        self.assertEqual(load_config(self.root)["site"]["name"], "example")


if __name__ == "__main__":
    unittest.main()
