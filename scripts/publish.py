#!/usr/bin/env python3
"""Publish the reviewed TRTalks source and release from a normal local terminal."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from build_release import ROOT, build

SOURCE_PATHS = [".gitignore", "README.md", "VERSION", "conversations.json", "setup.sh",
                "runtime", "skills", "scripts", "tests", "docs"]


def command(args, check=True):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Comando fallito: " + args[0])
    return result


def remote_name(value):
    match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?", value)
    return match.group(1).lower() if match else None


def verify_assets(repo, tag):
    with tempfile.TemporaryDirectory(prefix="trtalks-release-check-") as temporary:
        args = ["gh", "release", "download", tag, "--repo", repo, "--dir", temporary]
        names = ("trtalks.zip", "SHA256SUMS", "release.json", "setup.sh", "index.html")
        for name in names:
            args.extend(["--pattern", name])
        command(args)
        for name in names:
            remote = Path(temporary) / name
            if not remote.is_file() or remote.read_bytes() != (ROOT / "dist" / name).read_bytes():
                raise RuntimeError("Asset remoto diverso o mancante: " + name + ". Nessuna sovrascrittura automatica")


def publish(repo, dry_run=False):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Repository non valido: usare OWNER/REPO")
    base = "https://github.com/" + repo + "/releases/latest/download"
    metadata = build(ROOT / "dist", base)
    tag = "v" + metadata["version"]
    if dry_run:
        return {"published": False, "repository": repo, "version": metadata["version"],
                "install_command_after_publication": "curl --proto '=https' --proto-redir '=https' -fsSL " + base + "/setup.sh | bash"}
    # This preflight happens before Git or remote mutations. No shell or tokens in arguments.
    command(["gh", "auth", "status"])
    probe = command(["gh", "api", "repos/" + repo], check=False)
    missing = False
    if probe.returncode:
        if "HTTP 404" not in probe.stderr:
            raise RuntimeError(probe.stderr.strip() or "GitHub non raggiungibile")
        missing = True
    elif json.loads(probe.stdout).get("private") is not False:
        raise RuntimeError("Il repository esistente non è pubblico; nessuna visibilità modificata")
    command([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    git_root = command(["git", "rev-parse", "--show-toplevel"], check=False)
    if git_root.returncode:
        command(["git", "init", "-b", "main"])
    elif Path(git_root.stdout.strip()).resolve() != ROOT:
        raise RuntimeError("La cartella appartiene a un repository diverso")
    for key in ("user.name", "user.email"):
        if not command(["git", "config", "--get", key], check=False).stdout.strip():
            raise RuntimeError("Configurare l'identità Git locale prima di pubblicare: " + key)
    remotes = command(["git", "remote"]).stdout.split()
    if "origin" in remotes:
        origin = command(["git", "remote", "get-url", "origin"]).stdout.strip()
        if remote_name(origin) != repo.lower():
            raise RuntimeError("origin indica un altro repository; nessun collegamento modificato")
    else:
        command(["git", "remote", "add", "origin", "https://github.com/" + repo + ".git"])
    command(["git", "add", "--", *SOURCE_PATHS])
    if command(["git", "diff", "--cached", "--quiet"], check=False).returncode:
        command(["git", "commit", "-m", "Prepare TRTalks " + metadata["version"]])
    if command(["git", "status", "--porcelain"]).stdout.strip():
        raise RuntimeError("Restano file non salvati fuori dai sorgenti previsti; pubblicazione interrotta")
    head = command(["git", "rev-parse", "HEAD"]).stdout.strip()
    existing_tag = command(["git", "rev-parse", "--verify", "refs/tags/" + tag + "^{commit}"], check=False)
    if existing_tag.returncode:
        command(["git", "tag", "-a", tag, "-m", "TRTalks " + metadata["version"]])
    elif existing_tag.stdout.strip() != head:
        raise RuntimeError("Il tag esiste su un'altra revisione: incrementare VERSION, senza forzare il tag")
    branch = command(["git", "symbolic-ref", "--short", "HEAD"]).stdout.strip()
    if missing:
        command(["gh", "repo", "create", repo, "--public", "--description",
                 "TRTalks: skill locali Codex per conversazioni TechReloaded"])
    # Credentials are supplied by gh for this invocation, without changing global Git settings.
    git_push = ["git", "-c", "credential.helper=", "-c", "credential.https://github.com.helper=!gh auth git-credential", "push"]
    command([*git_push, "-u", "origin", "HEAD:refs/heads/" + branch])
    command([*git_push, "origin", "refs/tags/" + tag])
    release = command(["gh", "api", "repos/" + repo + "/releases/tags/" + tag], check=False)
    if release.returncode:
        if "HTTP 404" not in release.stderr:
            raise RuntimeError(release.stderr.strip())
        notes = ROOT / "dist/release-notes.md"
        notes.write_text("TRTalks " + metadata["version"] + "\n\nTRStory per case histories, catalogo di skill, runtime comune, installazione e aggiornamento con checksum.\n\nInvio SMTP locale con credenziali escluse dal pacchetto e conservate negli aggiornamenti. Retry incerti bloccati. Invio disabilitato alla prima installazione; configurare la password localmente. Voce e flusso completo da collaudare.\n", encoding="utf-8")
        assets = [str(ROOT / "dist" / name) for name in ("trtalks.zip", "SHA256SUMS", "release.json", "setup.sh", "index.html")]
        command(["gh", "release", "create", tag, *assets, "--repo", repo, "--verify-tag", "--draft",
                 "--title", "TRTalks " + metadata["version"], "--notes-file", str(notes)])
        draft = True
    else:
        draft = json.loads(release.stdout)["draft"]
    verify_assets(repo, tag)
    if draft:
        command(["gh", "release", "edit", tag, "--repo", repo, "--draft=false", "--latest"])
    command(["gh", "repo", "view", repo, "--json", "url"])
    return {"published": True, "repository_url": "https://github.com/" + repo,
            "release_url": "https://github.com/" + repo + "/releases/tag/" + tag,
            "install_command": "curl --proto '=https' --proto-redir '=https' -fsSL " + base + "/setup.sh | bash",
            "remote_installation_tested": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="AgileReloaded/TRTalks")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(publish(args.repo, args.dry_run), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({"published": False, "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
