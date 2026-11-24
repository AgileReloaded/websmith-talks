"""Conversation catalog and release file selection; no conversation-specific IDs."""
import json
from pathlib import PurePosixPath
import re

RUNTIME_FILES = {
    "runtime/catalog.py", "runtime/common.py", "runtime/manage.py", "runtime/trtalks.py",
    "runtime/send_document.py", "runtime/delivery.py",
    "runtime/references/backend.md", "runtime/references/invio.md",
}


def safe_relative(name):
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("Nome file non valido nel catalogo")
    path = PurePosixPath(name)
    if (path.is_absolute() or any(p in ("", ".", "..") or p.startswith(".") for p in name.split("/"))
            or name.endswith(".local.md") or "config.local" in name):
        raise ValueError("Percorso locale o non valido nel catalogo: " + name)
    return name


def validate_catalog(value):
    if not isinstance(value, dict) or value.get("schema") != 1:
        raise ValueError("Catalogo conversazioni non valido")
    entries = value.get("skills")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Il catalogo deve dichiarare almeno una skill")
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Voce del catalogo non valida")
        key = entry.get("id")
        if (not isinstance(key, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key)
                or len(key) > 64 or key in seen or key == "trtalks"):
            raise ValueError("ID skill duplicato, riservato o non valido: " + str(key))
        seen.add(key)
        for field in ("display_name", "description"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError("Metadati skill mancanti: " + field)
        files = entry.get("files")
        if (not isinstance(files, list) or not all(isinstance(f, str) for f in files)
                or len(files) != len(set(files)) or "SKILL.md" not in files):
            raise ValueError("Lista file non valida per " + key)
        for name in files:
            safe_relative(name)
    renames = value.get("renames", {})
    if not isinstance(renames, dict) or len(set(renames.values())) != len(renames):
        raise ValueError("Mappa delle rinomine non valida")
    for old, new in renames.items():
        if (not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", old)
                or old in seen or new not in seen):
            raise ValueError("Rinomina non valida nel catalogo")
    return value


def load_catalog(app):
    return validate_catalog(json.loads((app / "conversations.json").read_text(encoding="utf-8")))


def required_files(catalog):
    result = RUNTIME_FILES | {"conversations.json"}
    for entry in validate_catalog(catalog)["skills"]:
        result |= {"skills/" + entry["id"] + "/" + name for name in entry["files"]}
    return result


def skill_files(manifest, key):
    prefix = "skills/" + key + "/"
    return {name[len(prefix):]: sha for name, sha in manifest["files"].items() if name.startswith(prefix)}


def validate_skill_names(files, catalog):
    for entry in catalog["skills"]:
        name = "skills/" + entry["id"] + "/SKILL.md"
        pattern = rb"(?m)^name: " + re.escape(entry["id"].encode("ascii")) + rb"\s*$"
        if not re.search(pattern, files[name]):
            raise ValueError("Il nome della skill non corrisponde al catalogo: " + entry["id"])
