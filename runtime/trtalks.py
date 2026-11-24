#!/usr/bin/env python3
"""TRTalks command line entry point; works without third-party packages."""
import argparse
import json
from pathlib import Path
import sys

import manage
import send_document
from common import atomic_json, load_config, locked, plain_path, validate_config
from catalog import load_catalog

APPLICATION = Path(__file__).resolve().parent.parent


def version():
    manifest = APPLICATION / "release-manifest.json"
    if manifest.exists():
        return json.loads(manifest.read_text())["version"]
    return (APPLICATION / "VERSION").read_text().strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=version())
    parser.add_argument("--root", type=Path)
    parser.add_argument("command", choices=["update", "uninstall", "configure", "status", "probe",
                                           "dry-run", "send", "retry", "record-result", "skills", "paths"])
    args, remaining = parser.parse_known_args(argv)
    root = args.root or (APPLICATION.parent.parent if APPLICATION.parent.name == ".trtalks" else Path.cwd())
    root = root.expanduser().resolve()
    if args.command in ("skills", "paths"):
        if remaining:
            parser.error("Argomenti non riconosciuti: " + " ".join(remaining))
        app = root / ".trtalks/app"
        installed = app.exists()
        app = app if installed else APPLICATION
        catalog = load_catalog(app)
        if args.command == "skills":
            result = {"application": "TRTalks", "skills": [
                {"id": entry["id"], "display_name": entry["display_name"],
                 "description": entry["description"], "invoke": "$" + entry["id"]}
                for entry in catalog["skills"]]}
        else:
            metadata_path = root / ".trtalks/install.json"
            metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
            skill_root = app / "skills" if metadata.get("skills_in_application") or not installed else root / ".agents/skills"
            result = {"root": str(root), "application": str(app), "runtime": str(app / "runtime"),
                      "shared_references": str(app / "runtime/references"),
                      "skills": {entry["id"]: str(skill_root / entry["id"])
                                 for entry in catalog["skills"]}}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command in ("update", "uninstall"):
        return manage.main([args.command, "--root", str(root), *remaining])
    if args.command in ("send", "retry", "record-result", "dry-run", "status", "probe"):
        return send_document.main(["--root", str(root), args.command, *remaining])
    config_parser = argparse.ArgumentParser(prog="trtalks configure")
    config_parser.add_argument("--name")
    config_parser.add_argument("--email")
    config_parser.add_argument("--recipient")
    enabled = config_parser.add_mutually_exclusive_group()
    enabled.add_argument("--enable-send", action="store_true")
    enabled.add_argument("--disable-send", action="store_true")
    values = config_parser.parse_args(remaining)
    try:
        with locked(root / ".trtalks/manage.lock"):
            path = plain_path(root / ".trtalks/config.local.json")
            # Preserve unknown local keys; validate before committing any change.
            config = load_config(root)
            if values.name is not None:
                config["sender_name"] = values.name
            if values.email is not None:
                config["reply_to"] = values.email
            if values.recipient is not None:
                config["recipient"] = values.recipient
            if values.enable_send or values.disable_send:
                config["send_enabled"] = values.enable_send
            config = validate_config(config)
            atomic_json(path, config)
        print(json.dumps({"configured": True, "send_enabled": config["send_enabled"],
                          "transport": "gmail", "recipient": config["recipient"],
                          "config_file": str(path), "network_called": False}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, EOFError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
