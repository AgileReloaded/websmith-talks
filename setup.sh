#!/usr/bin/env bash
# Public HTTPS release bootstrap. Does not enable or send email.
set -euo pipefail
default_release_url=""
release_base="${WEBSMITH_TALKS_RELEASE_URL:-$default_release_url}"
install_root="${WEBSMITH_TALKS_HOME:-${TRTALKS_HOME:-$HOME/websmith-talks}}"
site_id="${WEBSMITH_TALKS_SITE_ID:-}"
site_name="${WEBSMITH_TALKS_SITE_NAME:-}"
site_url="${WEBSMITH_TALKS_SITE_URL:-}"
recipient="${WEBSMITH_TALKS_RECIPIENT:-}"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --site-id|--site-name|--site-url|--recipient|--root)
      [ "$#" -ge 2 ] || { echo "Valore mancante per $1" >&2; exit 1; }
      case "$1" in
        --site-id) site_id="$2" ;;
        --site-name) site_name="$2" ;;
        --site-url) site_url="$2" ;;
        --recipient) recipient="$2" ;;
        --root) install_root="$2" ;;
      esac
      shift 2 ;;
    --help|-h)
      echo 'Uso: bash setup.sh --site-id ID [--site-name NOME] [--site-url URL] [--recipient EMAIL] [--root CARTELLA]'
      echo 'Usare lo stesso site.id di websmith.yaml. Un sito diverso richiede una cartella separata.'
      exit 0 ;;
    *) echo "Opzione non riconosciuta: $1" >&2; exit 1 ;;
  esac
done
case "$(uname -s)" in Darwin|Linux) ;; *) echo 'Supportati macOS e Linux.' >&2; exit 1 ;; esac
for tool in python3 curl mktemp; do
  command -v "$tool" >/dev/null || { echo "Dipendenza richiesta: $tool" >&2; exit 1; }
done
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else "Serve Python 3.9+")'
[ -n "$release_base" ] || { echo 'Impostare WEBSMITH_TALKS_RELEASE_URL con la base HTTPS della release pubblicata.' >&2; exit 1; }
python3 - "$release_base" <<'PY'
import sys, urllib.parse
p = urllib.parse.urlsplit(sys.argv[1])
if not (p.scheme == 'https' and p.hostname and not (p.username or p.password or p.query or p.fragment)):
    raise SystemExit('URL release non valido')
PY
release_base="${release_base%/}"
temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT
for asset in SHA256SUMS websmith-talks.zip; do
  curl --proto '=https' --proto-redir '=https' -fsSL --connect-timeout 10 --max-time 90 \
    "$release_base/$asset" -o "$temporary/$asset"
done
# Verify the package before loading any package-supplied Python code.
expected=$(python3 - "$temporary" <<'PY'
from pathlib import Path
import hashlib, re, sys, zipfile
p = Path(sys.argv[1])
matches = re.findall(r'(?m)^([a-f0-9]{64})  websmith-talks\.zip$', (p/'SHA256SUMS').read_text(encoding='ascii'))
if len(matches) != 1:
    raise SystemExit('SHA256SUMS non valido')
if (p/'websmith-talks.zip').stat().st_size > 8*1024*1024:
    raise SystemExit('Pacchetto troppo grande')
if hashlib.sha256((p/'websmith-talks.zip').read_bytes()).hexdigest() != matches[0]:
    raise SystemExit('Checksum errato')
with zipfile.ZipFile(p/'websmith-talks.zip') as z:
    for name in ('manage.py', 'common.py', 'catalog.py'):
        member = z.getinfo('websmith-talks/runtime/' + name)
        if member.file_size >= 1024*1024:
            raise SystemExit('Bootstrap troppo grande')
        (p/name).write_bytes(z.read(member))
print(matches[0])
PY
)
site_args=(--interactive)
[ -z "$site_id" ] || site_args+=(--site-id "$site_id")
[ -z "$site_name" ] || site_args+=(--site-name "$site_name")
[ -z "$site_url" ] || site_args+=(--site-url "$site_url")
[ -z "$recipient" ] || site_args+=(--recipient "$recipient")
python3 "$temporary/manage.py" install --root "$install_root" --archive "$temporary/websmith-talks.zip" \
  --sha256 "$expected" --release-url "$release_base" --upgrade "${site_args[@]}"
echo "Apri la cartella $install_root nell'app Codex."
echo 'Scrivi: Mostrami le tipologie di conversazione websmith-talks disponibili.'
echo "Aggiornamento: $install_root/websmith-talks update"
echo 'Nessuna email inviata durante l’installazione.'
