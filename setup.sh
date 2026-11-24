#!/usr/bin/env bash
# Public HTTPS release bootstrap. Does not enable or send email.
set -euo pipefail
default_release_url=""
release_base="${TRTALKS_RELEASE_URL:-$default_release_url}"
install_root="${TRTALKS_HOME:-$HOME/TRTalks}"
case "$(uname -s)" in Darwin|Linux) ;; *) echo 'Supportati macOS e Linux.' >&2; exit 1 ;; esac
for tool in python3 curl mktemp; do
  command -v "$tool" >/dev/null || { echo "Dipendenza richiesta: $tool" >&2; exit 1; }
done
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else "Serve Python 3.9+")'
[ -n "$release_base" ] || { echo 'Impostare TRTALKS_RELEASE_URL con la base HTTPS della release pubblicata.' >&2; exit 1; }
python3 - "$release_base" <<'PY'
import sys, urllib.parse
p = urllib.parse.urlsplit(sys.argv[1])
if not (p.scheme == 'https' and p.hostname and not (p.username or p.password or p.query or p.fragment)):
    raise SystemExit('URL release non valido')
PY
release_base="${release_base%/}"
temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT
for asset in SHA256SUMS trtalks.zip; do
  curl --proto '=https' --proto-redir '=https' -fsSL --connect-timeout 10 --max-time 90 \
    "$release_base/$asset" -o "$temporary/$asset"
done
# Verify the package before loading any package-supplied Python code.
expected=$(python3 - "$temporary" <<'PY'
from pathlib import Path
import hashlib, re, sys, zipfile
p = Path(sys.argv[1])
matches = re.findall(r'(?m)^([a-f0-9]{64})  trtalks\.zip$', (p/'SHA256SUMS').read_text(encoding='ascii'))
if len(matches) != 1:
    raise SystemExit('SHA256SUMS non valido')
if (p/'trtalks.zip').stat().st_size > 8*1024*1024:
    raise SystemExit('Pacchetto troppo grande')
if hashlib.sha256((p/'trtalks.zip').read_bytes()).hexdigest() != matches[0]:
    raise SystemExit('Checksum errato')
with zipfile.ZipFile(p/'trtalks.zip') as z:
    for name in ('manage.py', 'common.py', 'catalog.py'):
        member = z.getinfo('trtalks/runtime/' + name)
        if member.file_size >= 1024*1024:
            raise SystemExit('Bootstrap troppo grande')
        (p/name).write_bytes(z.read(member))
print(matches[0])
PY
)
python3 "$temporary/manage.py" install --root "$install_root" --archive "$temporary/trtalks.zip" \
  --sha256 "$expected" --release-url "$release_base" --upgrade
echo "Apri la cartella $install_root nell'app Codex."
echo 'Scrivi: Mostrami le tipologie di conversazione TRTalks disponibili.'
echo "Aggiornamento: $install_root/trtalks update"
echo 'Invio email inizialmente disabilitato; nessuna email inviata durante l’installazione.'
