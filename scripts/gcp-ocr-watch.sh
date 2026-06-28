#!/usr/bin/env bash
# Poll GCS for OCR markdown + graph cache → sync locally until ingest complete.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/gcp-env.sh"
LOG="$ROOT/knowledge-graph/ingest-logs/gcp-sync-watch.log"
POLL="${GCP_SYNC_POLL_SEC:-60}"

mkdir -p "$ROOT/knowledge-graph/ingest-logs"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

pending_count() {
  local py="${PANCHANG_VENV:-/Users/ganesha/Projects/04-UX-Practice/Panchang/.venv}/bin/python"
  [[ -x "$py" ]] || py=python3
  "$py" - "$ROOT" <<'PY'
import sys
from pathlib import Path
ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "scripts"))
from core_jyotisha_titles import TEXT_BOOKS_MD, md_name_for_pdf
SOURCE = Path("/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/newbooks/CoreJyothisha")
RAW = ROOT / "knowledge-graph" / "raw"
n = 0
for pdf in sorted(SOURCE.glob("*.pdf")):
    md = md_name_for_pdf(pdf)
    if md in TEXT_BOOKS_MD:
        continue
    p = RAW / md
    if not p.is_file() or p.stat().st_size < 10000:
        n += 1
print(n)
PY
}

gcs_md_count() {
  gsutil ls "gs://${GCP_BUCKET}/markdown/" 2>/dev/null | grep -c '\.md$' || echo 0
}

gcs_graph_ready() {
  gsutil ls "gs://${GCP_BUCKET}/graphs/graph-deepseek.json" >/dev/null 2>&1
}

fleet_status() {
  local n=0 r=0
  for vm in vedicastro-ocr vedicastro-ocr-0 vedicastro-ocr-1 vedicastro-ocr-2; do
  st="$(gcloud compute instances describe "$vm" --zone="$GCP_ZONE" --format='get(status)' 2>/dev/null || true)"
    [[ -n "$st" ]] || continue
    n=$((n + 1))
    [[ "$st" == "RUNNING" ]] && r=$((r + 1))
  done
  echo "${r}/${n}"
}

log "gcp-sync-watch started bucket=gs://${GCP_BUCKET}/ poll=${POLL}s"

while true; do
  pend="$(pending_count)"
  gcs="$(gcs_md_count)"
  fleet="$(fleet_status)"
  graph="$(gcs_graph_ready && echo yes || echo no)"
  log "pending_scans=$pend gcs_md=$gcs fleet_running=$fleet gcs_graph=$graph"

  if [[ "$gcs" -gt 0 ]] || [[ "$graph" == "yes" ]]; then
    bash "$ROOT/scripts/gcp-sync-results.sh" >>"$LOG" 2>&1 || log "sync error (will retry)"
    pend="$(pending_count)"
  fi

  # Incremental DeepSeek on each new scan md (don't wait for all 14)
  if [[ "$pend" -lt 14 ]]; then
    PY="$PANCHANG_VENV/bin/python"
    if [[ -x "$PY" ]] && ! pgrep -f "deepseek-graph-extract.py run" >/dev/null 2>&1; then
      ready=$("$PY" - "$ROOT" <<'PY'
import sys
from pathlib import Path
ROOT=Path(sys.argv[1])
sys.path.insert(0,str(ROOT/"scripts"))
from core_jyotisha_titles import TEXT_BOOKS_MD, md_name_for_pdf
SRC=Path("/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/newbooks/CoreJyothisha")
RAW=ROOT/"knowledge-graph/raw"
mds=[md_name_for_pdf(p) for p in SRC.glob("*.pdf") if md_name_for_pdf(p) not in TEXT_BOOKS_MD and (RAW/md_name_for_pdf(p)).is_file()]
print(",".join(mds))
PY
)
      if [[ -n "$ready" ]]; then
        log "deepseek incremental on: $ready"
        INGEST_ONLY_MD="$ready" nohup "$PY" "$ROOT/scripts/deepseek-graph-extract.py" run --max-concurrency 4 \
          >>"$ROOT/knowledge-graph/ingest-logs/deepseek-ocr.log" 2>&1 </dev/null &
      fi
    fi
  fi

  if [[ "$pend" -eq 0 ]] && gcs_graph_ready; then
    log "ALL COMPLETE — scans + GCP graph synced"
    touch "$ROOT/knowledge-graph/ingest-logs/gcp-ocr-complete.marker"
    touch "$ROOT/knowledge-graph/ingest-logs/gcp-extract-complete.marker"
    "$PANCHANG_VENV/bin/python" "$ROOT/scripts/ingest-supervisor.py" --status >>"$LOG" 2>&1 || true
    exit 0
  fi

  sleep "$POLL"
done
