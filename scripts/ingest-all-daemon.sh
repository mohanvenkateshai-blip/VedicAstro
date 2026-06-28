#!/usr/bin/env bash
# Start all autonomous ingest daemons (supervisor + GCP OCR watch). Survives shell exit.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/knowledge-graph/ingest-logs"
mkdir -p "$LOG_DIR"

start_one() {
  local pattern="$1"
  local name="$2"
  shift 2
  if pgrep -f "$pattern" >/dev/null 2>&1; then
    echo "$name already running ($(pgrep -f "$pattern" | tr '\n' ' '))"
    return 0
  fi
  nohup "$@" >>"$LOG_DIR/${name}.log" 2>&1 </dev/null &
  local pid=$!
  disown 2>/dev/null || true
  echo "$name pid=$pid"
}

start_one "ingest-supervisor.py" "supervisor" \
  "${PANCHANG_VENV:-/Users/ganesha/Projects/04-UX-Practice/Panchang/.venv}/bin/python" \
  "$ROOT/scripts/ingest-supervisor.py"

start_one "gcp-ocr-watch.sh" "gcp-ocr-watch" \
  bash "$ROOT/scripts/gcp-ocr-watch.sh"

sleep 2
pgrep -fl "ingest-supervisor|gcp-ocr-watch" || true
