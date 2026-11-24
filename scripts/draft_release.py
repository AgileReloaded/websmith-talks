#!/usr/bin/env python3
"""Prepare a GitHub draft release for an existing, pushed tag. Never publishes."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

from build_release import ROOT, build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Repository pubblico esistente OWNER/REPO")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        parser.error("Repository non valido")
    version = (ROOT / "VERSION").read_text().strip()
    # Assets must correspond to the reviewed source tag, not a dirty checkout.
    clean = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True)
    if clean.returncode or clean.stdout.strip():
        parser.error("Servono un repository Git e sorgenti tutti salvati prima di preparare la release")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    tag = subprocess.run(["git", "rev-parse", "v" + version + "^{commit}"], cwd=ROOT, capture_output=True, text=True)
    if tag.returncode or tag.stdout.strip() != head:
        parser.error("Il tag locale v" + version + " deve indicare la revisione corrente e deve già essere pubblicato")
    base = "https://github.com/" + args.repo + "/releases/latest/download"
    build(ROOT / "dist", base)
    notes = ROOT / "dist/release-notes.md"
    notes.write_text("TRTalks " + version + "\n\nTRStory per case histories, catalogo di skill di conversazione e runtime comune. Installazione HTTPS con checksum, aggiornamento conservativo e consegna tramite send_email del connettore Gmail con allegato Markdown.\n\nAccount Google collegato nell’app; nessuna configurazione di server di posta locale. Collaudo remoto e vocale da verificare; vedere docs/SKILL-DI-CONVERSAZIONE.md.\n", encoding="utf-8")
    command = ["gh", "release", "create", "v" + version, "--repo", args.repo, "--verify-tag",
               "--draft", "--title", "TRTalks " + version, "--notes-file", str(notes)]
    command.extend(str(ROOT / "dist" / asset) for asset in ("trtalks.zip", "SHA256SUMS", "release.json", "setup.sh", "index.html"))
    return subprocess.run(command, cwd=ROOT).returncode


if __name__ == "__main__":
    sys.exit(main())
