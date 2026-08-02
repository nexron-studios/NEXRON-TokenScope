#!/usr/bin/env bash
# Startet den AI Usage Monitor lokal (Linux/macOS, u. a. Raspberry Pi).
#
#   ./start.sh          Backend + gebautes Frontend auf einem Port
#   ./start.sh --dev    zusaetzlich Vite-Dev-Server mit Hot-Reload auf 5173
#   ./start.sh --kiosk  danach Chromium im Vollbild starten
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
PYTHON="$BACKEND/.venv/bin/python"
PORT="${AIUSAGE_PORT:-8787}"

DEV=0
KIOSK=0
for arg in "$@"; do
  case "$arg" in
    --dev) DEV=1 ;;
    --kiosk) KIOSK=1 ;;
    *) echo "Unbekannte Option: $arg" >&2; exit 1 ;;
  esac
done

step() { printf '\033[36m==> %s\033[0m\n' "$1"; }

# --- Backend-Umgebung -------------------------------------------------------
if [ ! -x "$PYTHON" ]; then
  step 'Lege die Python-Umgebung an (einmalig)'
  python3 -m venv "$BACKEND/.venv"
  "$PYTHON" -m pip install --upgrade pip --quiet
  "$PYTHON" -m pip install -r "$BACKEND/requirements.txt" --quiet
fi

# --- Frontend ---------------------------------------------------------------
if [ ! -d "$FRONTEND/node_modules" ]; then
  step 'Installiere die npm-Pakete (einmalig)'
  (cd "$FRONTEND" && npm install)
fi

# Neu bauen, wenn der Build fehlt oder aelter als die Quellen ist.
needs_build=0
if [ ! -f "$FRONTEND/dist/index.html" ]; then
  needs_build=1
elif [ -n "$(find "$FRONTEND/src" -newer "$FRONTEND/dist/index.html" -print -quit)" ]; then
  needs_build=1
fi

if [ "$needs_build" -eq 1 ]; then
  step 'Baue das Frontend'
  (cd "$FRONTEND" && npm run build)
fi

# --- Start ------------------------------------------------------------------
pids=()
cleanup() { for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM

if [ "$DEV" -eq 1 ]; then
  step 'Starte den Vite-Dev-Server auf Port 5173'
  (cd "$FRONTEND" && npm run dev) &
  pids+=("$!")
fi

if [ "$KIOSK" -eq 1 ]; then
  (
    for _ in $(seq 1 40); do
      if curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
        chromium-browser --kiosk --incognito "http://127.0.0.1:$PORT/" 2>/dev/null ||
          chromium --kiosk --incognito "http://127.0.0.1:$PORT/" 2>/dev/null || true
        exit 0
      fi
      sleep 0.5
    done
  ) &
  pids+=("$!")
fi

step "Backend laeuft auf http://127.0.0.1:$PORT - Beenden mit Strg+C"
echo

# Bewusst kein `exec`: Sonst ersetzt uvicorn die Shell und der Trap oben
# koennte den Dev-Server nicht mehr mit beenden.
cd "$BACKEND"
PYTHONPATH="$BACKEND" "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
