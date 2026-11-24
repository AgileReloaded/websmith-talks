#!/usr/bin/env python3
"""Install one TRTalks application and all its declared conversation skills."""
import argparse
import ast
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import uuid
import zipfile

from catalog import required_files, safe_relative, skill_files, validate_catalog, validate_skill_names
from common import DEFAULT_CONFIG, canonical, digest, https_url, locked, plain_path, validate_config

MAX_ARCHIVE = 8 * 1024 * 1024
MANIFEST = "release-manifest.json"
LEGACY_REQUIRED = {"SKILL.md", "agents/openai.yaml", "scripts/trtalks.py", "scripts/manage.py",
                   "scripts/common.py", "scripts/send_document.py", "scripts/delivery.py",
                   "references/domande.md", "references/regole-resoconto.md", "references/backend.md",
                   "assets/resoconto.md", "references/invio.md"}


def version_key(version):
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?", version)
    if not match:
        raise ValueError("Versione non valida: " + str(version))
    major, minor, patch, stage, number = match.groups()
    return int(major), int(minor), int(patch), {"a": 0, "b": 1, "rc": 2, None: 3}[stage], int(number or 0)


def validate_manifest(manifest):
    if manifest.get("schema") != 2 or manifest.get("name") != "trtalks":
        raise ValueError("Manifest applicazione TRTalks non valido")
    version_key(manifest["version"])
    catalog = validate_catalog(manifest["catalog"])
    if set(manifest["files"]) != required_files(catalog):
        raise ValueError("Il manifest non corrisponde al catalogo delle skill")
    for name, sha in manifest["files"].items():
        safe_relative(name)
        if not re.fullmatch(r"[a-f0-9]{64}", sha):
            raise ValueError("Impronta di file non valida")
    return manifest


def read_archive(raw, expected):
    if len(raw) > MAX_ARCHIVE or not re.fullmatch(r"[a-f0-9]{64}", expected) or digest(raw) != expected:
        raise ValueError("Checksum o dimensione del pacchetto non valido")
    files = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if sum(i.file_size for i in archive.infolist()) > MAX_ARCHIVE or len(archive.infolist()) > 500:
            raise ValueError("Archivio troppo grande")
        for item in archive.infolist():
            if (item.is_dir() or not item.filename.startswith("trtalks/")
                    or stat.S_ISLNK(item.external_attr >> 16)):
                raise ValueError("Percorso non ammesso nell'archivio: " + item.filename)
            safe_relative(item.filename)
            relative = str(PurePosixPath(item.filename).relative_to("trtalks"))
            if relative in files:
                raise ValueError("File duplicato nell'archivio")
            files[relative] = archive.read(item)
    manifest = validate_manifest(json.loads(files.pop(MANIFEST)))
    if set(manifest["files"]) != set(files):
        raise ValueError("File mancanti o non dichiarati nel manifest")
    if json.loads(files["conversations.json"]) != manifest["catalog"]:
        raise ValueError("Catalogo della release non coerente")
    for name, raw_file in files.items():
        if digest(raw_file) != manifest["files"][name]:
            raise ValueError("Impronta errata: " + name)
        if name.endswith(".py"):
            ast.parse(raw_file.decode("utf-8"), filename=name)
    validate_skill_names(files, manifest["catalog"])
    files[MANIFEST] = canonical(manifest) + b"\n"
    return manifest, files


def installed_manifest(app):
    return validate_manifest(json.loads(plain_path(app / MANIFEST).read_text(encoding="utf-8")))


def check_tree(target, hashes, ignored=()):
    plain_path(target)
    found, local = set(), {}
    for path in target.rglob("*"):
        if path.is_symlink():
            raise ValueError("Link simbolico nell'installazione: " + str(path))
        if not path.is_file():
            continue
        relative = path.relative_to(target).as_posix()
        if "__pycache__" in path.parts and path.suffix == ".pyc":
            continue
        if relative.endswith(".local.md"):
            local[relative] = path.read_bytes()
            continue
        if relative in ignored:
            continue
        if relative not in hashes or digest(path.read_bytes()) != hashes[relative]:
            raise ValueError("File personalizzato o estraneo: " + str(path) + ". Nessun file sovrascritto")
        found.add(relative)
    if found != set(hashes):
        raise ValueError("Installazione incompleta: conservata senza modifiche")
    return local


def check_installed(app):
    manifest = installed_manifest(app)
    local = check_tree(app, manifest["files"], ignored=(MANIFEST,))
    if json.loads((app / "conversations.json").read_text()) != manifest["catalog"]:
        raise ValueError("Catalogo installato modificato")
    return manifest, local


def inspect_installation(root):
    app = plain_path(root / ".trtalks/app")
    if app.exists():
        manifest, local = check_installed(app)
        settings_path = root / ".trtalks/install.json"
        settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        in_application = settings.get("skills_in_application", False)
        skills = {}
        for entry in manifest["catalog"]["skills"]:
            key = entry["id"]
            target = (app / "skills" if in_application else root / ".agents/skills") / key
            skills[key] = {"target": target, "local": check_tree(target, skill_files(manifest, key))}
        return manifest, local, skills, False
    legacy = plain_path(root / ".agents/skills/trtalks")
    if legacy.exists():
        manifest = json.loads(plain_path(legacy / MANIFEST).read_text())
        if (manifest.get("schema") != 1 or manifest.get("name") != "trtalks"
                or not LEGACY_REQUIRED <= set(manifest["files"])):
            raise ValueError("La vecchia skill trtalks non è un'installazione gestita")
        version_key(manifest["version"])
        local = check_tree(legacy, manifest["files"], ignored=(MANIFEST,))
        return manifest, {}, {"trtalks": {"target": legacy, "local": local}}, True
    return None, {}, {}, False


def launcher_bytes(root, legacy=False):
    script = (root / ".agents/skills/trtalks/scripts/trtalks.py" if legacy
              else root / ".trtalks/app/runtime/trtalks.py")
    return ("#!/usr/bin/env python3\nimport os, sys\nos.execv(sys.executable, [sys.executable, "
            + repr(str(script)) + "] + sys.argv[1:])\n").encode("utf-8")


def guide_bytes(in_application=False):
    guide = ("# TRTalks\n\n"
        "Le tipologie di conversazione installate sono dichiarate in `.trtalks/app/conversations.json`.\n"
        "Leggere il catalogo quando l'utente chiede una conversazione TRTalks.\n"
        "Se la richiesta identifica una tipologia, usare il relativo SKILL.md in `.agents/skills/ID/`.\n"
        "Se è generica e c'è una sola skill, usare quella; con più skill chiedere quale, in una sola domanda.\n"
        "Non mescolare automaticamente domande e regole di skill diverse.\n"
        "Il comando `./trtalks skills` elenca nomi e prompt; `./trtalks paths` mostra i percorsi comuni.\n"
        "Le richieste tecniche non avviano conversazioni né autorizzano invii.\n").encode("utf-8")

    if in_application:
        guide = guide.replace(b".agents/skills/ID/", b".trtalks/app/skills/ID/")
        guide += ("\nUsare le istruzioni correnti nell’applicazione anche se una copia precedente della skill è presente in `.agents/skills/`.\n"
                  "La consegna usa esclusivamente send_email del connettore Gmail e le regole correnti in `.trtalks/app/runtime/references/invio.md`.\n").encode("utf-8")
    return guide


def commit_plan(plan, backup):
    history = []
    backup.mkdir(parents=True)
    try:
        for index, (target, staged) in enumerate(plan):
            plain_path(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            previous = backup / str(index)
            entry = {"target": target, "previous": previous, "created": False}
            history.append(entry)
            if target.exists():
                os.replace(target, previous)
            if staged is not None:
                os.replace(staged, target)
                entry["created"] = True
    except Exception:
        for entry in reversed(history):
            target = entry["target"]
            if entry["created"]:
                shutil.rmtree(target) if target.is_dir() else target.unlink()
            if entry["previous"].exists():
                os.replace(entry["previous"], target)
        raise


def staged_file(directory, name, data, mode=0o600):
    path = directory / name
    path.write_bytes(data)
    path.chmod(mode)
    return path


def install(root, raw, expected, release_url=None, update=False, dry_run=False, skills_in_application=False):
    root = Path(root).expanduser().resolve()
    manifest, files = read_archive(raw, expected)
    state = plain_path(root / ".trtalks")
    skill_root = plain_path(root / ".agents/skills")
    launcher = plain_path(root / "trtalks")
    if release_url:
        https_url(release_url)
    old, app_local, old_skills, legacy = inspect_installation(root)
    if old and not update:
        raise ValueError("TRTalks già installato; usare update o il nuovo setup con --upgrade")
    if update and not old:
        raise ValueError("TRTalks non installato")
    if launcher.exists() and launcher.read_bytes() != launcher_bytes(root, legacy):
        raise ValueError("Il file trtalks esistente non appartiene all'installer")
    for entry in manifest["catalog"]["skills"]:
        key = entry["id"]
        if plain_path(skill_root / key).exists() and key not in old_skills:
            raise ValueError("La skill " + key + " è già presente e non appartiene a TRTalks")
    if old and version_key(manifest["version"]) <= version_key(old["version"]):
        return {"changed": False, "version": old["version"], "reason": "already_current_or_newer"}
    if dry_run:
        return {"changed": False, "would_install": manifest["version"],
                "skills": [s["id"] for s in manifest["catalog"]["skills"]], "root": str(root)}
    with locked(state / "manage.lock"):
        current, app_local, old_skills, legacy = inspect_installation(root)
        if current != old:
            raise ValueError("Installazione cambiata durante il download; ripetere update")
        config = plain_path(state / "config.local.json")
        if config.exists() and not isinstance(json.loads(config.read_text()), dict):
            raise ValueError("Configurazione locale non valida; conservata")
        metadata_path = plain_path(state / "install.json")
        metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {"schema": 2}
        if not isinstance(metadata, dict):
            raise ValueError("Metadati di installazione non validi")
        skills_in_application = skills_in_application or metadata.get("skills_in_application", False)
        with tempfile.TemporaryDirectory(prefix="stage-", dir=str(state)) as temporary:
            temporary = Path(temporary)
            staged_app = temporary / "app"
            renames = manifest["catalog"].get("renames", {})
            if legacy:
                for name in ("backend", "invio"):
                    old_local = "references/" + name + ".local.md"
                    if old_local in old_skills["trtalks"]["local"]:
                        app_local["runtime/" + old_local] = old_skills["trtalks"]["local"].pop(old_local)
            for name, data in dict(files, **app_local).items():
                path = staged_app / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            result = subprocess.run([sys.executable, str(staged_app / "runtime/trtalks.py"), "--version"],
                capture_output=True, text=True, timeout=15, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            if result.returncode or result.stdout.strip() != manifest["version"]:
                raise ValueError("La release non supera la verifica di avvio: " + result.stderr[:300])
            plan = [(state / "app", staged_app)]
            new_ids = {entry["id"] for entry in manifest["catalog"]["skills"]}
            for key in sorted(new_ids):
                staged_skill = temporary / ("skill-" + key)
                shutil.copytree(staged_app / "skills" / key, staged_skill)
                previous_id = key if key in old_skills else next((k for k, v in renames.items() if v == key), None)
                for name, data in old_skills.get(previous_id, {}).get("local", {}).items():
                    path = staged_skill / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                if skills_in_application:
                    # App resources remain authoritative when .agents is protected.
                    shutil.copytree(staged_skill, staged_app / "skills" / key, dirs_exist_ok=True)
                else:
                    plan.append((skill_root / key, staged_skill))
            for key in sorted(set(old_skills) - new_ids) if not skills_in_application else ():
                plan.append((old_skills[key]["target"], None))
            plan.append((launcher, staged_file(temporary, "launcher", launcher_bytes(root), 0o755)))
            local_config = json.loads(config.read_text()) if config.exists() else {}
            migrated_config = validate_config(local_config)
            if not config.exists() or migrated_config != local_config:
                plan.append((config, staged_file(temporary, "config", canonical(migrated_config) + b"\n")))
            metadata.update(schema=2, installed=True, skills_in_application=skills_in_application)
            if release_url:
                metadata["release_url"] = release_url.rstrip("/")
            plan.append((metadata_path, staged_file(temporary, "metadata", canonical(metadata) + b"\n")))
            guide = plain_path(root / "AGENTS.md")
            if not guide.exists() or (skills_in_application and guide.read_bytes() == guide_bytes()):
                plan.append((guide, staged_file(temporary, "guide", guide_bytes(skills_in_application), 0o644)))
            elif skills_in_application and guide.read_bytes() != guide_bytes(True):
                raise ValueError("AGENTS.md personalizzato: specificare le skill dell’applicazione prima di attivare questa modalità")
            backup = state / "backups" / uuid.uuid4().hex
            commit_plan(plan, backup)
            # Rollback may need the original config, but successful migration must
            # not leave discarded connection passwords in the backup directory.
            for index, (target, _) in enumerate(plan):
                previous = backup / str(index)
                if target == config and previous.exists():
                    previous.unlink()
        return {"changed": True, "version": manifest["version"], "root": str(root),
                "skills": sorted(new_ids), "codex_recognition_verified": False,
                "local_configuration_preserved": True, "migrated_legacy_installation": legacy}


class HttpsRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme != "https" or parsed.username or parsed.password:
            raise ValueError("Redirect download non sicuro")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url, limit):
    https_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "TRTalks-Updater/0.3"})
    with urllib.request.build_opener(HttpsRedirect()).open(request, timeout=20) as response:
        if response.status != 200:
            raise ValueError("Download non riuscito")
        raw = response.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Download troppo grande")
    return raw


def remote_update(root, release_url=None, dry_run=False):
    root = Path(root).expanduser().resolve()
    current, _, _, _ = inspect_installation(root)
    if not current:
        raise ValueError("TRTalks non installato")
    settings = json.loads(plain_path(root / ".trtalks/install.json").read_text())
    base = release_url or settings.get("release_url")
    if not base:
        raise ValueError("URL di distribuzione mancante: specificare --release-url")
    base = https_url(base.rstrip("/"))
    sums = download(base + "/SHA256SUMS", 65536).decode("ascii")
    matches = re.findall(r"(?m)^([a-f0-9]{64})  trtalks\.zip$", sums)
    if len(matches) != 1:
        raise ValueError("SHA256SUMS non valido")
    return install(root, download(base + "/trtalks.zip", MAX_ARCHIVE), matches[0], base, update=True, dry_run=dry_run)


def uninstall(root):
    root = Path(root).expanduser().resolve()
    state = plain_path(root / ".trtalks")
    with locked(state / "manage.lock"):
        manifest, _, skills, legacy = inspect_installation(root)
        if not manifest:
            raise ValueError("TRTalks non installato")
        launcher = plain_path(root / "trtalks")
        if launcher.exists() and launcher.read_bytes() != launcher_bytes(root, legacy):
            raise ValueError("Launcher personalizzato: rimozione interrotta")
        path = plain_path(state / "install.json")
        metadata = json.loads(path.read_text())
        metadata["installed"] = False
        with tempfile.TemporaryDirectory(prefix="uninstall-", dir=str(state)) as temporary:
            temporary = Path(temporary)
            plan = [] if metadata.get("skills_in_application") else [(entry["target"], None) for entry in skills.values()]
            if not legacy:
                plan.append((state / "app", None))
            if launcher.exists():
                plan.append((launcher, None))
            guide = plain_path(root / "AGENTS.md")
            if guide.exists() and guide.read_bytes() == guide_bytes(metadata.get("skills_in_application", False)):
                plan.append((guide, None))
            plan.append((path, staged_file(temporary, "metadata", canonical(metadata) + b"\n")))
            backup = state / "backups" / ("uninstalled-" + uuid.uuid4().hex)
            commit_plan(plan, backup)
    return {"uninstalled": True, "removed_skills": list(skills),
            "drafts_configuration_and_delivery_state_preserved": True, "backup": str(backup)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("install", "update", "uninstall"):
        part = commands.add_parser(command)
        part.add_argument("--root", type=Path, default=Path.home() / "TRTalks")
        if command != "uninstall":
            part.add_argument("--release-url")
            part.add_argument("--dry-run", action="store_true")
            part.add_argument("--archive", type=Path)
            part.add_argument("--sha256")
        if command == "install":
            part.add_argument("--upgrade", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "uninstall":
            result = uninstall(args.root)
        elif args.archive:
            if not args.sha256:
                raise ValueError("Specificare --sha256 per il pacchetto locale")
            with args.archive.open("rb") as stream:
                raw = stream.read(MAX_ARCHIVE + 1)
            update = args.command == "update"
            if getattr(args, "upgrade", False):
                update = inspect_installation(args.root.expanduser().resolve())[0] is not None
            result = install(args.root, raw, args.sha256, args.release_url, update, args.dry_run)
        elif args.command == "update":
            result = remote_update(args.root, args.release_url, args.dry_run)
        else:
            raise ValueError("L'installazione iniziale richiede un archivio verificato da setup.sh")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
