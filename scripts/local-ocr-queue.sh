#!/usr/bin/env bash
# Local parallel OCR for pending CoreJyothisha scans (smallest PDFs first).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/gcp-env.sh"
PY="$PANCHANG_VENV/bin/python"
SOURCE="/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/newbooks/CoreJyothisha"
RAW="$ROOT/knowledge-graph/raw"
LOG="$ROOT/knowledge-graph/ingest-logs/local-ocr.log"
PARALLEL="${LOCAL_OCR_PARALLEL:-4}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

log "local OCR queue parallel=$PARALLEL"

while IFS= read -r job; do
  [[ -n "$job" ]] || continue
  IFS='|' read -r pdf md <<< "$job"
  echo "$pdf|$md"
done < <("$PY" - "$SOURCE" "$RAW" "$ROOT" <<'PY'
import sys
from pathlib import Path
import fitz
SOURCE, RAW, ROOT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(ROOT / "scripts"))
from core_jyotisha_titles import TEXT_BOOKS_MD, md_name_for_pdf

pending = []
for pdf in sorted(SOURCE.glob("*.pdf")):
    md = md_name_for_pdf(pdf)
    if md in TEXT_BOOKS_MD or (RAW / md).is_file():
        continue
    pages = len(fitz.open(pdf))
    if pages > 500:
        continue
    pending.append((pages, pdf, md))
for _, pdf, md in sorted(pending):
    print(f"{pdf}|{md}")
PY
) > /tmp/vedicastro-local-ocr.jobs

if [[ ! -s /tmp/vedicastro-local-ocr.jobs ]]; then
  log "no local OCR jobs (all done or deferred to GCP)"
  exit 0
fi

running=0
while IFS= read -r job; do
  IFS='|' read -r pdf md <<< "$job"
  (
    log "start $md"
    if "$PY" "$ROOT/scripts/gcp-fast-pdf-to-md.py" "$pdf" "$RAW/$md" --workers 4; then
      log "done $md"
      gsutil -q cp "$RAW/$md" "gs://${GCP_BUCKET}/markdown/$md" 2>/dev/null || true
    else
      log "fail $md"
    fi
  ) &
  running=$((running + 1))
  if [[ $running -ge $PARALLEL ]]; then
    wait -n 2>/dev/null || wait
    running=$((running - 1))
  fi
done < /tmp/vedicastro-local-ocr.jobs

wait
log "local OCR queue finished"
