"""Shared standard-library helpers for the macOS/Linux TRTalks runtime."""
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
    "recipient": "trtalks@techreloaded.it",
    "sender_name": "TRTalks",
    "reply_to": "",
    "send_enabled": True,
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
    if not email_address(result["recipient"]):
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


def load_config(root):
    path = plain_path(Path(root) / ".trtalks" / "config.local.json")
    value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return validate_config(value)
