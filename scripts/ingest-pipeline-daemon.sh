#!/usr/bin/env bash
# Long-running ingest daemon — do NOT exit (launchd KeepAlive).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/gcp-env.sh"
LOG_DIR="$ROOT/knowledge-graph/ingest-logs"
mkdir -p "$LOG_DIR"
PY="$PANCHANG_VENV/bin/python"
[[ -x "$PY" ]] || PY=python3

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_DIR/pipeline-daemon.log"; }

log "pipeline daemon started PATH=$PATH"

# Supervisor (phase orchestration)
if ! pgrep -f "ingest-supervisor.py" >/dev/null 2>&1; then
  nohup "$PY" "$ROOT/scripts/ingest-supervisor.py" >>"$LOG_DIR/supervisor.log" 2>&1 </dev/null &
  log "started supervisor pid=$!"
fi

# GCS sync watcher
if ! pgrep -f "gcp-ocr-watch.sh" >/dev/null 2>&1; then
  nohup bash "$ROOT/scripts/gcp-ocr-watch.sh" >>"$LOG_DIR/gcp-sync-watch.log" 2>&1 </dev/null &
  log "started gcp-sync-watch pid=$!"
fi

# Local OCR for pending scans (parallel backup — smallest books first)
if ! pgrep -f "local-ocr-queue.sh" >/dev/null 2>&1; then
  nohup bash "$ROOT/scripts/local-ocr-queue.sh" >>"$LOG_DIR/local-ocr.log" 2>&1 </dev/null &
  log "started local-ocr-queue pid=$!"
fi

# Stay alive — relaunch children if they die (one instance each)
while true; do
  sleep 30
  if ! pgrep -f "ingest-supervisor.py" >/dev/null 2>&1; then
    log "supervisor died — restarting"
    nohup "$PY" "$ROOT/scripts/ingest-supervisor.py" >>"$LOG_DIR/supervisor.log" 2>&1 </dev/null &
  fi
  # Only one sync watcher
  nwatch=$(pgrep -fc "gcp-ocr-watch.sh" 2>/dev/null || echo 0)
  if [[ "$nwatch" -lt 1 ]]; then
    log "sync-watch died — restarting"
    nohup bash "$ROOT/scripts/gcp-ocr-watch.sh" >>"$LOG_DIR/gcp-sync-watch.log" 2>&1 </dev/null &
  elif [[ "$nwatch" -gt 1 ]]; then
    pgrep -f "gcp-ocr-watch.sh" | tail -n +2 | xargs kill 2>/dev/null || true
  fi
  if ! pgrep -f "local-ocr-queue.sh" >/dev/null 2>&1; then
    pend=$("$PY" - "$ROOT" <<'PY'
import sys
from pathlib import Path
ROOT=Path(sys.argv[1])
sys.path.insert(0,str(ROOT/"scripts"))
from core_jyotisha_titles import TEXT_BOOKS_MD, md_name_for_pdf
SRC=Path("/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/newbooks/CoreJyothisha")
RAW=ROOT/"knowledge-graph/raw"
print(sum(1 for p in SRC.glob("*.pdf") if md_name_for_pdf(p) not in TEXT_BOOKS_MD and not (RAW/md_name_for_pdf(p)).is_file()))
PY
)
    if [[ "$pend" -gt 0 ]]; then
      log "local-ocr died with $pend pending — restarting"
      nohup bash "$ROOT/scripts/local-ocr-queue.sh" >>"$LOG_DIR/local-ocr.log" 2>&1 </dev/null &
    fi
  fi
done
