#!/usr/bin/env bash
# Detached daemon wrapper — survives Cursor shell exit (setsid + nohup).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/knowledge-graph/ingest-logs/supervisor.log"
PY="$ROOT/../Panchang/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="${PANCHANG_VENV:-/Users/ganesha/Projects/04-UX-Practice/Panchang/.venv}/bin/python"
fi
if [[ ! -x "$PY" ]]; then
  echo "error: Panchang venv python not found" >&2
  exit 1
fi
mkdir -p "$ROOT/knowledge-graph/ingest-logs"
if pgrep -f "ingest-supervisor.py" >/dev/null 2>&1; then
  echo "supervisor already running"
  pgrep -fl "ingest-supervisor.py"
  exit 0
fi
nohup "$PY" "$ROOT/scripts/ingest-supervisor.py" >>"$LOG" 2>&1 </dev/null &
disown 2>/dev/null || true
echo "supervisor pid=$! (detached)"
sleep 2
tail -3 "$LOG"
