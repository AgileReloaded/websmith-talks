#!/usr/bin/env python3
"""Build an allowlisted, deterministic TRTalks release without private files."""
import argparse
import hashlib
import html
import io
import json
import re
from pathlib import Path
import shlex
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))
from common import canonical, https_url
from catalog import load_catalog, required_files
from manage import read_archive, version_key


def package(version, source=None):
    version_key(version)
    source = source or ROOT
    catalog = load_catalog(source)
    files = {}
    for name in sorted(required_files(catalog)):
        path = source / name
        if path.is_symlink():
            raise ValueError("Link nella distribuzione: " + name)
        files[name] = path.read_bytes()
    manifest = {"schema": 2, "name": "trtalks", "version": version, "catalog": catalog,
                "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()}}
    files["release-manifest.json"] = canonical(manifest) + b"\n"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo("trtalks/" + name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    raw = buffer.getvalue()
    checksum = hashlib.sha256(raw).hexdigest()
    read_archive(raw, checksum)
    return raw, checksum


def build(output, release_url=None):
    version = (ROOT / "VERSION").read_text().strip()
    raw, checksum = package(version)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "trtalks.zip").write_bytes(raw)
    (output / "SHA256SUMS").write_text(checksum + "  trtalks.zip\n", encoding="ascii")
    (output / "release.json").write_bytes(canonical({"version": version, "asset": "trtalks.zip", "sha256": checksum}) + b"\n")
    setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
    if release_url:
        setup = setup.replace('default_release_url=""', "default_release_url=" + shlex.quote(https_url(release_url.rstrip("/"))))
    (output / "setup.sh").write_text(setup, encoding="utf-8")
    page = (ROOT / "docs/installazione.html").read_text(encoding="utf-8")
    skills_html = "<ul>" + "".join(
        "<li><strong>" + html.escape(entry["display_name"]) + "</strong> — "
        + html.escape(entry["description"]) + "<br><code>Usa $" + entry["id"] + "</code></li>"
        for entry in load_catalog(ROOT)["skills"]) + "</ul>"
    page = re.sub(r"<!-- trtalks:skills -->.*?<!-- /trtalks:skills -->",
                  lambda _: "<!-- trtalks:skills -->" + skills_html + "<!-- /trtalks:skills -->", page, flags=re.S)
    if release_url:
        page = page.replace('name="trtalks-release-url" content=""',
                            'name="trtalks-release-url" content="' + html.escape(release_url.rstrip("/"), quote=True) + '"')
    (output / "index.html").write_text(page, encoding="utf-8")
    return {"version": version, "archive": str((output / "trtalks.zip").resolve()),
            "sha256": checksum, "published": False, "default_release_url": release_url}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--release-url")
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.release_url), ensure_ascii=False, indent=2))
