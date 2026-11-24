"""Shared standard-library helpers for the macOS/Linux websmith-talks runtime."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.parse

DEFAULT_CONFIG = {
    "schema": 2,
    "transport": "gmail",
    "recipient": "",
    "sender_name": "websmith-talks",
    "reply_to": "",
    "send_enabled": True,
    "site": None,
}



def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def https_url(url):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.fragment or parsed.query):
        raise ValueError("Serve un URL HTTPS senza credenziali, query o frammento")
    return url


def plain_path(path):
    path = Path(path)
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError("Percorso simbolico non ammesso: " + str(item))
    return path


def atomic_json(path, value):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("File di stato simbolico: " + str(path))
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".write-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(canonical(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def locked(path):
    path = plain_path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Un'altra operazione è in corso; nessun secondo invio avviato")
        yield
    finally:
        os.close(fd)


def email_address(value):
    return (isinstance(value, str) and len(value.encode("utf-8")) <= 254
            and re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", value))


def validate_site(value):
    if not isinstance(value, dict) or set(value) - {"id", "name", "base_url"}:
        raise ValueError("Configurazione site non valida")
    key = value.get("id")
    # Same pattern as Websmith's websmith-site.schema.json and init command.
    if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", key):
        raise ValueError("site.id non valido: copiare il valore di Websmith, con lettere minuscole, numeri e trattini")
    result = dict(value)
    result.setdefault("name", key)
    result.setdefault("base_url", "")
    if (not isinstance(result["name"], str) or not result["name"].strip()
            or re.search(r"[\x00-\x1f\x7f]", result["name"])):
        raise ValueError("Nome del sito non valido")
    url = result["base_url"]
    if not isinstance(url, str):
        raise ValueError("Indirizzo del sito non valido")
    if url:
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or re.search(r"[\x00-\x20\x7f]", url)):
            raise ValueError("Indirizzo del sito non valido: usare http/https senza credenziali, query o frammenti")
    return result


def site_tag(site):
    return "[websmith:" + validate_site(site)["id"] + "]"


def bind_site(config, requested=None, required=False):
    result = dict(config)
    current = result.get("site")
    if requested is not None:
        if current and isinstance(requested, dict):
            requested = dict(current, **requested)
        requested = validate_site(requested)
        if current and current["id"] != requested["id"]:
            raise ValueError("Installazione già associata al sito " + current["id"] + "; per un altro sito usare una cartella separata")
        result["site"] = requested
    if required and not result.get("site"):
        raise ValueError("Sito non configurato: specificare --site-id con lo stesso site.id di Websmith")
    return result


def requested_site(config, key=None, name=None, url=None):
    if key is None and name is None and url is None:
        return None
    result = dict(config.get("site") or {})
    if key is not None:
        result["id"] = key
    if name is not None:
        result["name"] = name
    if url is not None:
        result["base_url"] = url
    return validate_site(result)


def validate_config(value):
    if not isinstance(value, dict) or type(value.get("schema", 1)) is not int or value.get("schema", 1) not in (1, 2):
        raise ValueError("Configurazione locale non valida")
    # Drop legacy connection credentials rather than carrying them into Gmail.
    result = {k: v for k, v in value.items()
              if not k.startswith(("smtp_", "http_", "mcp_"))
              and k not in ("endpoint", "api_key", "token", "authorization")}
    legacy = value.get("schema", 1) == 1
    if not legacy and value.get("transport", "gmail") != "gmail":
        raise ValueError("Trasporto supportato: gmail")
    result = dict(DEFAULT_CONFIG, **result)
    result.update(schema=2, transport="gmail")
    if result["site"] is not None:
        result["site"] = validate_site(result["site"])
    if result["recipient"] != "" and not email_address(result["recipient"]):
        raise ValueError("Destinatario non valido")
    for field in ("sender_name", "reply_to"):
        if not isinstance(result[field], str):
            raise ValueError(field + " deve essere una stringa")
    if result["reply_to"] and not email_address(result["reply_to"]):
        raise ValueError("Reply-To non valido")
    if (len(result["sender_name"].encode("utf-8")) > 200
            or re.search(r"[\x00-\x1f\x7f]", result["sender_name"])):
        raise ValueError("Nome mittente non valido, massimo 200 byte UTF-8")
    if type(result["send_enabled"]) is not bool:
        raise ValueError("send_enabled deve essere booleano")
    return result


def installation_config(state):
    state = plain_path(Path(state))
    path = plain_path(state / "config.local.json")
    value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    result = validate_config(value)
    metadata = plain_path(state / "install.json")
    if metadata.exists():
        data = json.loads(metadata.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Metadati di installazione non validi")
        if data.get("site") is not None:
            recorded = validate_site(data["site"])
            if result["site"] and result["site"]["id"] != recorded["id"]:
                raise ValueError("site.id differisce dal sito associato all'installazione")
            if result["site"] is None:
                result["site"] = recorded
    return result


def load_config(root):
    if plain_path(Path(root) / ".trtalks").exists():
        raise ValueError("Installazione TRTalks da migrare: eseguire il nuovo installer con --upgrade prima di usare websmith-talks")
    return installation_config(Path(root) / ".websmith-talks")
