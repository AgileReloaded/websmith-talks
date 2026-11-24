#!/usr/bin/env python3
"""Prepare an authorized Gmail call and retain the real connector receipt.

The agent calls the ChatGPT connector. Local Python only prepares arguments;
preparation is never reported as a sent email.
"""
import argparse
import json
from pathlib import Path
import re
import sys
import uuid

from common import atomic_json, canonical, digest, email_address, load_config, locked, now, plain_path
from delivery import GMAIL_TOOL, gmail_arguments, gmail_receipt


def status(root):
    config = load_config(root)
    return {"operation": "gmail-status", "transport": "gmail", "network_called": False,
            "recipient": config["recipient"], "send_enabled": config["send_enabled"],
            "gmail_connection_verified": False, "email_delivery": "not_requested",
            "required_tool": GMAIL_TOOL,
            "next_action": "L'agente verifica il tool Gmail; get_profile verifica l'account senza inviare email."}


def validated_document(file, config, name=None, email=None):
    file = plain_path(Path(file).absolute())
    if not file.is_file():
        raise ValueError("La bozza deve essere un file regolare")
    with file.open("rb") as stream:
        raw = stream.read(262145)
    text = raw.decode("utf-8")
    if not text.strip() or len(raw) > 262144 or b"\0" in raw:
        raise ValueError("Markdown vuoto, troppo grande o contenente NUL")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}\.md", file.name):
        raise ValueError("Nome file non valido: usare lettere, numeri, _ o - e .md")
    name = config["sender_name"] if name is None else name
    email = config["reply_to"] if email is None else email
    if (not isinstance(name, str) or len(name.encode("utf-8")) > 200
            or re.search(r"[\x00-\x1f\x7f]", name)):
        raise ValueError("Nome autore non valido")
    if not isinstance(email, str) or (email and not email_address(email)):
        raise ValueError("Reply-To non valido")
    return {"name": name, "email": email, "filename": file.name, "markdown": text}, digest(raw)


def dry_run(root, file, name=None, email=None):
    config = load_config(root)
    args, sha = validated_document(file, config, name, email)
    return {"network_called": False, "email_delivery": "not_requested", "transport": "gmail",
            "sha256": sha, "bytes": len(args["markdown"].encode("utf-8")),
            "filename": args["filename"], "recipient": config["recipient"],
            "send_enabled": config["send_enabled"], "required_tool": GMAIL_TOOL}


def probe(root):
    target = plain_path(Path(root) / "artifacts/prova-gmail.md")
    raw = "# Prova TRTalks\n\nDocumento fittizio per verificare il formato.\n".encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as stream:
            stream.write(raw)
    except FileExistsError:
        if target.read_bytes() != raw:
            raise ValueError("Il documento di prova esiste con altro contenuto; non sovrascritto")
    return {"verified": True, "network_called": False, "email_delivery": "not_requested",
            "draft_path": str(target), "sha256": digest(raw), "bytes": len(raw)}


def record_path(root, request_id):
    if not re.fullmatch(r"trtalks-[a-f0-9]{32}", request_id):
        raise ValueError("request_id non valido")
    return plain_path(Path(root) / ".trtalks/deliveries" / (request_id + ".json"))


def cached_result(record, path):
    return dict(record["outcome"], cached=True, local_status="accepted", state_file=str(path),
                network_called=False, next_action="Nessun nuovo invio: riusare la ricevuta salvata.")


def send(root, file, approved_sha256, authorization, name=None, email=None):
    root = Path(root).resolve()
    config = load_config(root)
    if not config["send_enabled"]:
        raise ValueError("Invio disabilitato nella configurazione locale")
    args, sha = validated_document(file, config, name, email)
    if approved_sha256 != sha or not isinstance(authorization, str) or not authorization.strip():
        raise ValueError("Manca l'autorizzazione esplicita o la bozza differisce dalla versione autorizzata")
    with locked(root / ".trtalks/delivery.lock"):
        directory = plain_path(root / ".trtalks/deliveries")
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        fingerprint = digest(canonical({"recipient": config["recipient"], "arguments": args}))
        for path in directory.glob("trtalks-*.json"):
            record = json.loads(plain_path(path).read_text(encoding="utf-8"))
            if record["document_sha256"] != sha:
                continue
            if record.get("transport") != "gmail":
                raise ValueError("Documento registrato con un precedente trasporto: verificare manualmente; nessun reinvio Gmail")
            if record["fingerprint"] != fingerprint:
                raise ValueError("Documento registrato con altri metadati o destinatario: verificare prima di un altro invio")
            if record["status"] == "accepted":
                return cached_result(record, path)
            raise ValueError("Tentativo già preparato o esito incerto: verificare Gmail, nessun reinvio automatico. ID: " + record["request_id"])
        request_id = "trtalks-" + uuid.uuid4().hex
        # Keep exactly the authorized bytes if the original is edited later.
        snapshot_dir = plain_path(directory / request_id)
        snapshot_dir.mkdir(mode=0o700)
        attachment = snapshot_dir / args["filename"]
        with attachment.open("xb") as stream:
            stream.write(args["markdown"].encode("utf-8"))
        attachment.chmod(0o600)
        tool_args = gmail_arguments(config["recipient"], attachment, args["filename"], args["name"], args["email"])
        record = {"schema": 3, "transport": "gmail", "created_at": now(), "request_id": request_id,
                  "recipient": config["recipient"], "document_sha256": sha, "fingerprint": fingerprint,
                  "authorization": authorization, "draft_path": str(Path(file).absolute()),
                  "attachment_path": str(attachment), "arguments": args, "gmail_arguments": tool_args,
                  "status": "pending"}
        path = record_path(root, request_id)
        atomic_json(path, record)
        return {"request_id": request_id, "transport": "gmail", "local_status": "pending",
                "network_called": False, "email_sent": False, "email_delivery": "not_requested",
                "cached": False, "state_file": str(path), "tool": GMAIL_TOOL, "tool_arguments": tool_args,
                "next_action": "L'agente chiama adesso il tool Gmail e registra la risposta con record-result. Questo comando non ha inviato email."}


def record_result(root, request_id, receipt_file):
    with locked(Path(root) / ".trtalks/delivery.lock"):
        path = record_path(root, request_id)
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("transport") != "gmail" or record.get("request_id") != request_id:
            raise ValueError("La ricevuta deve riferirsi a un tentativo Gmail dello stesso ID")
        if record["status"] == "accepted":
            return cached_result(record, path)
        if record["status"] not in ("pending", "uncertain"):
            raise ValueError("Stato del tentativo inatteso")
        raw_receipt = json.loads(plain_path(receipt_file).read_text(encoding="utf-8"))
        record["connector_result"] = raw_receipt
        record["updated_at"] = now()
        try:
            receipt = gmail_receipt(raw_receipt)
            record["status"] = "accepted"
            outcome = {"request_id": request_id, "gmail_accepted": True, "message_id": receipt["id"],
                       "recipient": record["recipient"], "email_delivery": "unconfirmed", "cached": False}
            record["receipt"] = receipt
        except (ValueError, TypeError, KeyError):
            record["status"] = "uncertain"
            outcome = {"request_id": request_id, "gmail_accepted": False, "email_delivery": "unconfirmed",
                       "error": "Gmail non ha confermato l'invio: verificare manualmente prima di un nuovo tentativo"}
        record["outcome"] = outcome
        atomic_json(path, record)
        return dict(outcome, local_status=record["status"], state_file=str(path), network_called=False)


def retry(root, request_id):
    with locked(Path(root) / ".trtalks/delivery.lock"):
        path = record_path(root, request_id)
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("transport") == "gmail" and record["status"] == "accepted":
            return cached_result(record, path)
        raise ValueError("Reinvio automatico disabilitato: verificare l'esito nel servizio originale; nessuna email inviata")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    commands.add_parser("probe")
    for command in ("dry-run", "send"):
        part = commands.add_parser(command)
        part.add_argument("file", type=Path)
        part.add_argument("--name")
        part.add_argument("--email")
        if command == "send":
            part.add_argument("--approved-sha256", required=True)
            part.add_argument("--authorization", required=True)
    commands.add_parser("retry").add_argument("request_id")
    receipt = commands.add_parser("record-result")
    receipt.add_argument("request_id")
    receipt.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = status(args.root)
        elif args.command == "probe":
            result = probe(args.root)
        elif args.command == "dry-run":
            result = dry_run(args.root, args.file, args.name, args.email)
        elif args.command == "send":
            result = send(args.root, args.file, args.approved_sha256, args.authorization, args.name, args.email)
        elif args.command == "record-result":
            result = record_result(args.root, args.request_id, args.receipt)
        else:
            result = retry(args.root, args.request_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("local_status") == "uncertain" else 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"ok": False, "error": str(error), "email_delivery": "unconfirmed"
                          if args.command in ("send", "retry", "record-result") else "not_requested"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
