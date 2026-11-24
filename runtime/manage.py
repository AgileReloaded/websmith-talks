#!/usr/bin/env python3
"""Install one websmith-talks application and all its declared conversation skills."""
import argparse
import ast
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import shlex
import stat
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import uuid
import zipfile

from catalog import required_files, safe_relative, skill_files, validate_catalog, validate_skill_names
from common import DEFAULT_CONFIG, bind_site, canonical, digest, https_url, installation_config, locked, plain_path, requested_site, site_tag, validate_config

MAX_ARCHIVE = 8 * 1024 * 1024
MANIFEST = "release-manifest.json"
DEFAULT_RELEASE_URL = "https://github.com/AgileReloaded/websmith-talks/releases/latest/download"
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


def validate_manifest(manifest, allow_trtalks=False):
    names = ("websmith-talks", "trtalks") if allow_trtalks else ("websmith-talks",)
    if manifest.get("schema") != 2 or manifest.get("name") not in names:
        raise ValueError("Manifest applicazione websmith-talks non valido")
    version_key(manifest["version"])
    catalog = validate_catalog(manifest["catalog"])
    if set(manifest["files"]) != required_files(catalog, manifest["name"]):
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
            if (item.is_dir() or not item.filename.startswith("websmith-talks/")
                    or stat.S_ISLNK(item.external_attr >> 16)):
                raise ValueError("Percorso non ammesso nell'archivio: " + item.filename)
            safe_relative(item.filename)
            relative = str(PurePosixPath(item.filename).relative_to("websmith-talks"))
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
    return validate_manifest(json.loads(plain_path(app / MANIFEST).read_text(encoding="utf-8")), allow_trtalks=True)


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


def installation_state(root):
    state = plain_path(root / ".websmith-talks")
    previous = plain_path(root / ".trtalks")
    if previous.exists():
        if state.exists():
            raise ValueError("Sono presenti sia .trtalks sia .websmith-talks: verificare le installazioni prima di procedere")
        return previous
    return state


def inspect_installation(root):
    state = installation_state(root)
    app = plain_path(state / "app")
    if app.exists():
        manifest, local = check_installed(app)
        settings_path = plain_path(state / "install.json")
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


def launcher_bytes(root, legacy=False, trtalks=False):
    script = (root / ".agents/skills/trtalks/scripts/trtalks.py" if legacy
              else root / ".trtalks/app/runtime/trtalks.py" if trtalks
              else root / ".websmith-talks/app/runtime/websmith_talks.py")
    return ("#!/usr/bin/env python3\nimport os, sys\nos.execv(sys.executable, [sys.executable, "
            + repr(str(script)) + "] + sys.argv[1:])\n").encode("utf-8")


def legacy_guide_bytes(in_application=False, with_site=True):
    # Keep the exact previously distributed bytes to recognize managed guides.
    guide = ("# websmith-talks\n\n"
        "Le tipologie di conversazione installate sono dichiarate in `.websmith-talks/app/conversations.json`.\n"
        "Leggere il catalogo quando l'utente chiede una conversazione websmith-talks.\n"
        "Se la richiesta identifica una tipologia, usare il relativo SKILL.md in `.agents/skills/ID/`.\n"
        "Se è generica e c'è una sola skill, usare quella; con più skill chiedere quale, in una sola domanda.\n"
        "Non mescolare automaticamente domande e regole di skill diverse.\n"
        "Il comando `./websmith-talks skills` elenca nomi e prompt; `./websmith-talks paths` mostra i percorsi comuni.\n"
        "Le richieste tecniche non avviano conversazioni né autorizzano invii.\n").encode("utf-8")

    if in_application:
        guide = guide.replace(b".agents/skills/ID/", b".websmith-talks/app/skills/ID/")
        guide += ("\nUsare le istruzioni correnti nell’applicazione anche se una copia precedente della skill è presente in `.agents/skills/`.\n"
                  "La consegna usa esclusivamente send_email del connettore Gmail e le regole correnti in `.websmith-talks/app/runtime/references/invio.md`.\n").encode("utf-8")
    if with_site:
        guide += ("\nPrima di una conversazione leggere `./websmith-talks status`: `site` identifica l’unico sito associato.\n"
                  "Non chiedere di scegliere un altro sito e non cambiare site.id. Se manca, richiedere l’ID di Websmith e usare configure --site-id.\n"
                  "Le consegne email devono usare il tag [websmith:site.id] preparato dal runtime.\n").encode("utf-8")
    return guide


def guide_bytes(in_application=False, with_site=True):
    guide = legacy_guide_bytes(in_application, with_site)
    guide = guide.replace("Le richieste tecniche non avviano conversazioni né autorizzano invii.".encode("utf-8"),
                          "Le sole verifiche tecniche non avviano interviste e non spediscono email.".encode("utf-8"))
    guide += ("\n## Installazione corrente e richieste tecniche\n\n"
        "Usare questa installazione locale di websmith-talks e la sua configurazione per tutte le richieste, anche vocali.\n"
        "Il nome del sito non identifica un'altra applicazione o una cartella da cercare.\n"
        "Per verifiche, prove email e consegne leggere prima `./websmith-talks status` e `./websmith-talks paths`.\n"
        "Leggere `.websmith-talks/app/runtime/references/invio.md` e `.websmith-talks/app/runtime/references/backend.md`, anche senza avviare Story o Page.\n"
        "Usare send_email del connettore Gmail disponibile nella sessione: il mittente è l'account collegato nell'app del collega.\n"
        "Leggere il destinatario effettivo da status; nelle nuove installazioni è trtalks@techreloaded.it.\n"
        "Story prevede la consegna automatica del Markdown alla fine dell'intervista, salvo richiesta di non inviare.\n"
        "Annunciare destinatario e consegna all'inizio; alla conclusione mostrare il documento e completare l'invio senza una seconda conferma.\n"
        "Una sola verifica tecnica o prova della skill non invia email; una richiesta esplicita di creare e inviare una prova segue invece il flusso di consegna.\n"
        "Se manca un accesso o uno strumento, indicare l'operazione tentata e il limite effettivo; non dedurre che manchi la cartella e non rinviare automaticamente a un'altra chat.\n").encode("utf-8")
    return guide


def previous_guide_bytes(in_application=False):
    # The generated guide from TRTalks; custom project instructions stay intact.
    return legacy_guide_bytes(in_application, with_site=False).replace(b"websmith-talks", b"trtalks").replace(b"# trtalks", b"# TRTalks").replace(
        b"conversazione trtalks.", b"conversazione TRTalks.")


def merge_local(target, name, data):
    if name in target and target[name] != data:
        raise ValueError("Personalizzazioni in conflitto durante la rinomina: " + name)
    target[name] = data


def copy_preserved(source, target):
    plain_path(source)
    if source.is_dir():
        for child in source.rglob("*"):
            plain_path(child)
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)


def renamed_overrides(source, target, renames):
    # Merge old IDs only when their local files agree; never discard a conflict.
    for child in source.rglob("*"):
        plain_path(child)
        relative = child.relative_to(source)
        destination = target / renames.get(relative.parts[0], relative.parts[0])
        destination = destination.joinpath(*relative.parts[1:])
        if child.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif destination.exists():
            if destination.read_bytes() != child.read_bytes():
                raise ValueError("Personalizzazioni in conflitto: " + str(relative))
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, destination)


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


def install(root, raw, expected, release_url=None, update=False, dry_run=False, skills_in_application=False, site=None, recipient=None, source_root=None):
    root = Path(root).expanduser().resolve()
    manifest, files = read_archive(raw, expected)
    state = plain_path(root / ".websmith-talks")
    skill_root = plain_path(root / ".agents/skills")
    launcher = plain_path(root / "websmith-talks")
    if release_url:
        https_url(release_url)
    old_state = installation_state(root)
    migrating = old_state != state
    old, app_local, old_skills, legacy = inspect_installation(root)
    if migrating and not old:
        raise ValueError("La cartella .trtalks non contiene un'installazione gestita; conservata senza modifiche")
    if old and not update:
        raise ValueError("websmith-talks già installato; usare update o il nuovo setup con --upgrade")
    if update and not old:
        raise ValueError("websmith-talks non installato")
    previous_config = installation_config(old_state)
    selected_config = bind_site(previous_config, site, required=True)
    if recipient is not None:
        selected_config["recipient"] = recipient
    selected_config = validate_config(selected_config)
    previous_metadata_path = plain_path(old_state / "install.json")
    previous_metadata = json.loads(previous_metadata_path.read_text()) if previous_metadata_path.exists() else {}
    source_change = (source_root is not None and previous_metadata.get("source_root") != str(Path(source_root).expanduser().resolve()))
    source_change = source_change or (source_root is None and release_url is not None and "source_root" in previous_metadata)
    if launcher.exists() and (migrating or launcher.read_bytes() != launcher_bytes(root)):
        raise ValueError("Il file websmith-talks esistente non appartiene all'installer")
    old_launcher = plain_path(root / "trtalks") if migrating else None
    if old_launcher and old_launcher.exists() and old_launcher.read_bytes() != launcher_bytes(root, legacy, trtalks=True):
        raise ValueError("Launcher trtalks personalizzato: migrazione interrotta")
    for entry in manifest["catalog"]["skills"]:
        key = entry["id"]
        if plain_path(skill_root / key).exists() and key not in old_skills:
            raise ValueError("La skill " + key + " è già presente e non appartiene a websmith-talks")
    if (old and old["name"] == manifest["name"]
            and (version_key(manifest["version"]) < version_key(old["version"])
                 or (version_key(manifest["version"]) == version_key(old["version"]) and selected_config == previous_config
                     and not source_change and not (source_root and old["files"] != manifest["files"])))):
        return {"changed": False, "version": old["version"], "reason": "already_current_or_newer"}
    if dry_run:
        return {"changed": False, "would_install": manifest["version"],
                "site": selected_config["site"], "email_tag": site_tag(selected_config["site"]),
                "skills": [s["id"] for s in manifest["catalog"]["skills"]], "root": str(root)}
    with locked(old_state / "manage.lock"), locked(old_state / "delivery.lock"):
        current, app_local, old_skills, legacy = inspect_installation(root)
        if current != old:
            raise ValueError("Installazione cambiata durante il download; ripetere update")
        if installation_config(old_state) != previous_config:
            raise ValueError("Configurazione cambiata durante il download; ripetere update")
        config = plain_path(old_state / "config.local.json")
        if config.exists() and not isinstance(json.loads(config.read_text()), dict):
            raise ValueError("Configurazione locale non valida; conservata")
        metadata_path = plain_path(old_state / "install.json")
        metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {"schema": 2}
        if not isinstance(metadata, dict):
            raise ValueError("Metadati di installazione non validi")
        skills_in_application = skills_in_application or metadata.get("skills_in_application", False)
        with tempfile.TemporaryDirectory(prefix=".websmith-talks-stage-", dir=str(root)) as temporary:
            temporary = Path(temporary)
            staged_app = temporary / "app"
            renames = manifest["catalog"].get("renames", {})
            if legacy:
                for name in ("backend", "invio"):
                    old_local = "references/" + name + ".local.md"
                    if old_local in old_skills["trtalks"]["local"]:
                        app_local["runtime/" + old_local] = old_skills["trtalks"]["local"].pop(old_local)
            renamed_local = {}
            for name, data in app_local.items():
                parts = name.split("/")
                if parts[0] == "skills":
                    parts[1] = renames.get(parts[1], parts[1])
                merge_local(renamed_local, "/".join(parts), data)
            for name, data in dict(files, **renamed_local).items():
                path = staged_app / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            result = subprocess.run([sys.executable, str(staged_app / "runtime/websmith_talks.py"), "--version"],
                capture_output=True, text=True, timeout=15, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            if result.returncode or result.stdout.strip() != manifest["version"]:
                raise ValueError("La release non supera la verifica di avvio: " + result.stderr[:300])
            plan = [(state / "app", staged_app)]
            overrides = plain_path(old_state / "overrides")
            if overrides.exists():
                staged_overrides = temporary / "overrides"
                staged_overrides.mkdir()
                renamed_overrides(overrides, staged_overrides, renames)
                plan.append((state / "overrides", staged_overrides))
            if migrating:
                if (old_state / "backups").exists() and (old_state / "legacy-backups").exists():
                    raise ValueError("Sono presenti backups e legacy-backups: conservati senza fusione automatica")
                for child in old_state.iterdir():
                    plain_path(child)
                    if child.name in ("app", "config.local.json", "install.json", "manage.lock", "overrides"):
                        continue
                    target = temporary / ("preserved-" + child.name)
                    copy_preserved(child, target)
                    # Historical backups remain separate from the new rollback backup.
                    destination = state / ("legacy-backups" if child.name == "backups" else child.name)
                    plan.append((destination, target))
            new_ids = {entry["id"] for entry in manifest["catalog"]["skills"]}
            for key in sorted(new_ids):
                staged_skill = temporary / ("skill-" + key)
                shutil.copytree(staged_app / "skills" / key, staged_skill)
                local = {}
                for previous_id, previous in old_skills.items():
                    if renames.get(previous_id, previous_id) == key:
                        for name, data in previous["local"].items():
                            merge_local(local, name, data)
                for name, data in local.items():
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
            if old_launcher and old_launcher.exists():
                plan.append((old_launcher, None))
            local_config = json.loads(config.read_text()) if config.exists() else {}
            migrated_config = selected_config
            if migrating or not config.exists() or migrated_config != local_config:
                config_bytes = config.read_bytes() if config.exists() and migrated_config == local_config else canonical(migrated_config) + b"\n"
                plan.append((state / "config.local.json", staged_file(temporary, "config", config_bytes)))
            metadata.update(schema=2, installed=True, skills_in_application=skills_in_application, site=migrated_config["site"])
            if source_root is not None:
                metadata["source_root"] = str(Path(source_root).expanduser().resolve())
            elif release_url:
                metadata.pop("source_root", None)
            if release_url:
                metadata["release_url"] = release_url.rstrip("/")
            elif migrating and metadata.get("release_url", "").startswith("https://github.com/AgileReloaded/TRTalks/releases/"):
                metadata["release_url"] = DEFAULT_RELEASE_URL
            else:
                metadata.setdefault("release_url", DEFAULT_RELEASE_URL)
            plan.append((state / "install.json", staged_file(temporary, "metadata", canonical(metadata) + b"\n")))
            guide = plain_path(root / "AGENTS.md")
            generated_guides = (guide_bytes(), guide_bytes(True),
                                legacy_guide_bytes(), legacy_guide_bytes(True),
                                legacy_guide_bytes(False, False), legacy_guide_bytes(True, False),
                                previous_guide_bytes(), previous_guide_bytes(True))
            if not guide.exists() or guide.read_bytes() in generated_guides:
                plan.append((guide, staged_file(temporary, "guide", guide_bytes(skills_in_application), 0o644)))
            elif skills_in_application and guide.read_bytes() != guide_bytes(True):
                raise ValueError("AGENTS.md personalizzato: specificare le skill dell’applicazione prima di attivare questa modalità")
            if migrating:
                # Removed last so rollback can restore the complete original installation.
                plan.append((old_state, None))
            state.mkdir(mode=0o700, exist_ok=True)
            backup = state / "backups" / uuid.uuid4().hex
            try:
                commit_plan(plan, backup)
            except Exception:
                if migrating:
                    # Remove only empty directories left by a successful rollback.
                    # Any recovery files from an incomplete rollback stay available.
                    for directory in sorted((p for p in state.rglob("*") if p.is_dir()),
                                            key=lambda p: len(p.parts), reverse=True):
                        try:
                            directory.rmdir()
                        except OSError:
                            pass
                    try:
                        state.rmdir()
                    except OSError:
                        pass
                raise
            # Rollback may need the original config, but successful migration must
            # not leave discarded connection passwords in the backup directory.
            for index, (target, _) in enumerate(plan):
                previous = backup / str(index)
                if target == state / "config.local.json" and previous.exists():
                    previous.unlink()
                if migrating and target == old_state and migrated_config != local_config:
                    previous_config = previous / "config.local.json"
                    if previous_config.exists():
                        previous_config.unlink()
        return {"changed": True, "version": manifest["version"], "root": str(root),
                "site": selected_config["site"], "email_tag": site_tag(selected_config["site"]),
                "skills": sorted(new_ids), "codex_recognition_verified": False,
                "local_configuration_preserved": True, "migrated_legacy_installation": legacy,
                "migrated_trtalks_installation": migrating}


class HttpsRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme != "https" or parsed.username or parsed.password:
            raise ValueError("Redirect download non sicuro")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url, limit):
    https_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "websmith-talks-Updater/0.8"})
    with urllib.request.build_opener(HttpsRedirect()).open(request, timeout=20) as response:
        if response.status != 200:
            raise ValueError("Download non riuscito")
        raw = response.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Download troppo grande")
    return raw


def source_install(root, source, *, update=False, dry_run=False, site=None, recipient=None):
    source = plain_path(Path(source).expanduser().resolve())
    builder = plain_path(source / "scripts/build_release.py")
    if not builder.is_file():
        raise ValueError("Sorgenti locali non disponibili: " + str(source) + "; usare --release-url per una release pubblicata")
    with tempfile.TemporaryDirectory(prefix="websmith-talks-source-") as directory:
        output = Path(directory)
        result = subprocess.run([sys.executable, str(builder), "--output", str(output)],
            capture_output=True, text=True, timeout=60,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        if result.returncode:
            raise ValueError("Build dei sorgenti non riuscita: " + result.stderr[:500])
        metadata = json.loads((output / "release.json").read_text())
        raw = (output / "websmith-talks.zip").read_bytes()
        return install(root, raw, metadata["sha256"], update=update, dry_run=dry_run,
                       site=site, recipient=recipient, source_root=source)


def remote_install(root, release_url=None, *, update=False, dry_run=False, site=None, recipient=None):
    base = https_url((release_url or DEFAULT_RELEASE_URL).rstrip("/"))
    sums = download(base + "/SHA256SUMS", 65536).decode("ascii")
    matches = re.findall(r"(?m)^([a-f0-9]{64})  websmith-talks\.zip$", sums)
    if len(matches) != 1:
        raise ValueError("SHA256SUMS non valido")
    return install(root, download(base + "/websmith-talks.zip", MAX_ARCHIVE), matches[0], base,
                   update=update, dry_run=dry_run, site=site, recipient=recipient)


def remote_update(root, release_url=None, dry_run=False, site=None, recipient=None):
    root = Path(root).expanduser().resolve()
    current, _, _, _ = inspect_installation(root)
    if not current:
        raise ValueError("websmith-talks non installato")
    settings = json.loads(plain_path(installation_state(root) / "install.json").read_text())
    base = release_url or settings.get("release_url")
    if not release_url and current["name"] == "trtalks" and (not base or base.startswith("https://github.com/AgileReloaded/TRTalks/releases/")):
        base = DEFAULT_RELEASE_URL
    if not base:
        raise ValueError("URL di distribuzione mancante: specificare --release-url")
    return remote_install(root, base, update=True, dry_run=dry_run, site=site, recipient=recipient)


def command_bytes(fallback=None, legacy=False):
    fallback_code = repr(str(fallback)) if fallback is not None else 'str(Path(__file__).resolve().parent / "runtime/websmith_talks.py")'
    code = '''#!/usr/bin/env python3
# Managed websmith-talks command __VERSION__
import os
from pathlib import Path
import sys

FALLBACK = __FALLBACK__
arguments = sys.argv[1:]
explicit_root = None
command = None
index = 0
while index < len(arguments):
    item = arguments[index]
    if item == "--root" and index + 1 < len(arguments):
        explicit_root = arguments[index + 1]
        index += 2
        continue
    if item.startswith("--root="):
        explicit_root = item.split("=", 1)[1]
    elif command is None and not item.startswith("-"):
        command = item
    index += 1
root = Path(explicit_root).expanduser().resolve() if explicit_root else Path.cwd()
if not explicit_root and command not in ("install", "command-install"):
    for candidate in (root, *root.parents):
        if (candidate / ".websmith-talks").exists() or (candidate / ".trtalks").exists():
            root = candidate
            break
runtime = root / ".websmith-talks/app/runtime/websmith_talks.py"
__ROUTING__
    runtime = Path(FALLBACK)
if not runtime.is_file():
    sys.exit("Runtime websmith-talks non disponibile: registrare nuovamente il comando da un'installazione o dai sorgenti.")
os.execv(sys.executable, [sys.executable, str(runtime), "--root", str(root), *arguments])
'''
    routing = 'if not runtime.is_file() or command in ("install", "update", "command-install"):'
    if legacy:
        routing = ('source_command = (Path(FALLBACK).parent.parent / "scripts/build_release.py").is_file()\n'
                   'if (not runtime.is_file() or command in ("install", "command-install")\n'
                   '        or (command == "update" and source_command)):')
    return code.replace("__FALLBACK__", fallback_code).replace("__VERSION__", "v1" if legacy else "v2").replace("__ROUTING__", routing).encode("utf-8")


def register_command(fallback, bin_dir=None):
    fallback = plain_path(Path(fallback).expanduser().resolve())
    if not fallback.is_file():
        raise ValueError("Runtime del comando non disponibile")
    directory = plain_path(Path(bin_dir or os.environ.get("WEBSMITH_TALKS_BIN_DIR") or Path.home() / ".local/bin").expanduser().resolve())
    target = plain_path(directory / "websmith-talks")
    raw = command_bytes(fallback)
    if target.exists() and target.read_bytes() != raw:
        previous = target.read_bytes()
        try:
            tree = ast.parse(previous.decode("utf-8"))
            assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                              and any(isinstance(t, ast.Name) and t.id == "FALLBACK" for t in n.targets))
            old_fallback = ast.literal_eval(assignment.value)
            managed = isinstance(old_fallback, str) and previous in (command_bytes(old_fallback), command_bytes(old_fallback, legacy=True))
        except (ValueError, SyntaxError, StopIteration, UnicodeError):
            managed = False
        if not managed:
            raise ValueError("Il comando esistente è personalizzato o appartiene a un altro programma; conservato: " + str(target))
    if not target.exists() or target.read_bytes() != raw:
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".websmith-talks-command-", dir=str(directory)) as temporary:
            staged = staged_file(Path(temporary), "command", raw, 0o755)
            os.replace(staged, target)
    in_path = any(Path(p).expanduser().resolve() == directory for p in os.environ.get("PATH", "").split(os.pathsep) if p)
    return {"command_installed": True, "command_path": str(target), "directory_in_path": in_path,
            "path_command": None if in_path else 'export PATH=' + shlex.quote(str(directory)) + ':"$PATH"'}


def uninstall(root):
    root = Path(root).expanduser().resolve()
    if installation_state(root).name == ".trtalks":
        raise ValueError("Usare il launcher trtalks originale oppure completare la migrazione prima della disinstallazione")
    state = plain_path(root / ".websmith-talks")
    with locked(state / "manage.lock"):
        manifest, _, skills, legacy = inspect_installation(root)
        if not manifest:
            raise ValueError("websmith-talks non installato")
        launcher = plain_path(root / "websmith-talks")
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
    parser = argparse.ArgumentParser(prog="websmith-talks", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("install", "update", "uninstall"):
        part = commands.add_parser(command)
        part.add_argument("--root", type=Path, default=Path.home() / "websmith-talks")
        if command != "uninstall":
            part.add_argument("--source", type=Path, help="Sorgenti locali; non scarica una release")
            part.add_argument("--site-id")
            part.add_argument("--site-name")
            part.add_argument("--site-url")
            part.add_argument("--recipient")
            part.add_argument("--release-url")
            part.add_argument("--dry-run", action="store_true")
            part.add_argument("--archive", type=Path)
            part.add_argument("--sha256")
        if command == "install":
            part.add_argument("--upgrade", action="store_true")
            part.add_argument("--interactive", action="store_true")
    args = parser.parse_args(argv)
    try:
        site = None
        if args.command != "uninstall":
            current_config = installation_config(installation_state(args.root.expanduser().resolve()))
            if (getattr(args, "interactive", False) and current_config["site"] is None
                    and (args.site_id is None or args.site_name is None)):
                try:
                    with open("/dev/tty", "r", encoding="utf-8") as reader, open("/dev/tty", "w", encoding="utf-8", buffering=1) as writer:
                        if args.site_id is None:
                            writer.write("Identificativo del sito da usare (site.id di Websmith): ")
                            writer.flush()
                            answer = reader.readline()
                            if not answer:
                                raise ValueError("Installazione interrotta: identificativo del sito non ricevuto")
                            args.site_id = answer.strip()
                        if args.site_name is None:
                            writer.write("Nome del sito [" + args.site_id + "]: ")
                            writer.flush()
                            answer = reader.readline()
                            if not answer:
                                raise ValueError("Installazione interrotta: nome del sito non ricevuto")
                            args.site_name = answer.strip() or args.site_id
                except OSError:
                    if args.site_id is None:
                        raise ValueError("Specificare --site-id oppure WEBSMITH_TALKS_SITE_ID per l'installazione non interattiva")
            site = requested_site(current_config, args.site_id, args.site_name, args.site_url)
        if args.command == "uninstall":
            result = uninstall(args.root)
        elif args.source:
            if args.archive or args.release_url:
                raise ValueError("Usare --source oppure --archive/--release-url, senza combinarli")
            update = args.command == "update"
            if getattr(args, "upgrade", False):
                update = inspect_installation(args.root.expanduser().resolve())[0] is not None
            result = source_install(args.root, args.source, update=update, dry_run=args.dry_run, site=site, recipient=args.recipient)
        elif args.archive:
            if not args.sha256:
                raise ValueError("Specificare --sha256 per il pacchetto locale")
            with args.archive.open("rb") as stream:
                raw = stream.read(MAX_ARCHIVE + 1)
            update = args.command == "update"
            if getattr(args, "upgrade", False):
                update = inspect_installation(args.root.expanduser().resolve())[0] is not None
            result = install(args.root, raw, args.sha256, args.release_url, update, args.dry_run, site=site, recipient=args.recipient)
        elif args.command == "update":
            result = remote_update(args.root, args.release_url, args.dry_run, site=site, recipient=args.recipient)
        else:
            update = getattr(args, "upgrade", False) and inspect_installation(args.root.expanduser().resolve())[0] is not None
            result = remote_install(args.root, args.release_url, update=update, dry_run=args.dry_run, site=site, recipient=args.recipient)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
