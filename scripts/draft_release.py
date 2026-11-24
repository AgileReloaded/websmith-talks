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
    notes.write_text("websmith-talks " + version + "\n\nDestinatario base trtalks@techreloaded.it per le nuove installazioni. Story consegna automaticamente il Markdown a fine intervista tramite il Gmail collegato nell’app del collega, salvo richiesta di sola bozza o non invio. Istruzioni comuni anche per prove email e richieste tecniche, senza cercare un altro progetto dal nome del sito. Gli aggiornamenti riconoscono le istruzioni generate precedenti e conservano i destinatari personalizzati. Comandi websmith-talks install e websmith-talks update, registrazione nel terminale, installazione e aggiornamento dalle release GitHub su ogni computer; sorgenti locali solo con --source esplicito. Skill story e page e stato in .websmith-talks. Un sito per installazione, site.id condiviso con Websmith e tag email [websmith:site.id]. Il setup richiede --site-id; gli aggiornamenti conservano il sito e rifiutano un ID diverso. Migrazione delle installazioni TRTalks con il nuovo installer, conservando configurazione, documenti, regole locali e ricevute.\n\nInstallazione HTTPS con checksum, aggiornamento conservativo e consegna tramite send_email del connettore Gmail con allegato Markdown. Account Google collegato nell’app, nessuna configurazione di server di posta locale. Voce e riconoscimento delle skill da collaudare nell’app.\n", encoding="utf-8")
    command = ["gh", "release", "create", "v" + version, "--repo", args.repo, "--verify-tag",
               "--draft", "--title", "websmith-talks " + version, "--notes-file", str(notes)]
    command.extend(str(ROOT / "dist" / asset) for asset in ("websmith-talks.zip", "SHA256SUMS", "release.json", "setup.sh", "index.html"))
    return subprocess.run(command, cwd=ROOT).returncode


if __name__ == "__main__":
    sys.exit(main())
