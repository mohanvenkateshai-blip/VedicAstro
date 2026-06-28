#!/usr/bin/env bash
# EMERGENCY: OCR all pending CoreJyothisha scans NOW — max parallelism, no waiting.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/gcp-env.sh"
PY="$PANCHANG_VENV/bin/python"
SOURCE="/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/newbooks/CoreJyothisha"
RAW="$ROOT/knowledge-graph/raw"
LOG="$ROOT/knowledge-graph/ingest-logs/ocr-blast.log"
PARALLEL="${OCR_BLAST_PARALLEL:-8}"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

# Kill stuck prior OCR
pkill -f "gcp-fast-pdf-to-md.py" 2>/dev/null || true
sleep 1

log "BLAST START parallel=$PARALLEL"

$PY - "$SOURCE" "$RAW" "$ROOT" <<'PY' > /tmp/vedicastro-blast.jobs
import sys
from pathlib import Path
import fitz
SOURCE, RAW, ROOT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(ROOT / "scripts"))
from core_jyotisha_titles import TEXT_BOOKS_MD, md_name_for_pdf

for pdf in sorted(SOURCE.glob("*.pdf")):
    md = md_name_for_pdf(pdf)
    if md in TEXT_BOOKS_MD:
        continue
    out = RAW / md
    if out.is_file() and out.stat().st_size > 10000:
        continue
    pages = len(fitz.open(pdf))
    print(f"{pages}|{pdf}|{md}")
PY

n=$(wc -l < /tmp/vedicastro-blast.jobs | tr -d ' ')
log "$n books to OCR"

running=0
while IFS='|' read -r pages pdf md; do
  [[ -n "$pdf" ]] || continue
  log "→ $md ($pages pages)"
  (
    if "$PY" "$ROOT/scripts/gcp-fast-pdf-to-md.py" "$pdf" "$RAW/$md" --workers 8 --dpi 120; then
      log "✓ $md"
      gsutil -q cp "$RAW/$md" "gs://${GCP_BUCKET}/markdown/$md" || true
      # Immediate DeepSeek on this book
      INGEST_ONLY_MD="$md" "$PY" "$ROOT/scripts/deepseek-graph-extract.py" run --max-concurrency 6 \
        >>"$ROOT/knowledge-graph/ingest-logs/deepseek-blast-$md.log" 2>&1 &
    else
      log "✗ $md"
    fi
  ) &
  running=$((running + 1))
  [[ $running -lt $PARALLEL ]] || { wait -n 2>/dev/null || wait; running=$((running - 1)); }
done < /tmp/vedicastro-blast.jobs

wait
log "BLAST OCR done — merging graph"
"$PY" "$ROOT/scripts/deepseek-graph-extract.py" merge
"$PY" - "$ROOT" <<'PY'
import json, sys
from pathlib import Path
ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "scripts"))
from graph_extract_common import merge_graph, merge_caches_into, GRAPH_BASE, update_manifest
base = json.loads(GRAPH_BASE.read_text())
merged, _ = merge_caches_into(base, ROOT / "knowledge-graph/graphify-out/cache/deepseek")
for extra in ("graph-deepseek.json", "graph-gemini.json"):
    p = ROOT / "knowledge-graph/graphify-out" / extra
    if p.is_file():
        merged = merge_graph(merged, json.loads(p.read_text()))
out = ROOT / "knowledge-graph/graphify-out/graph-core-jyotisha.json"
out.write_text(json.dumps(merged, indent=2))
print(f"MERGED {len(merged['nodes'])} nodes → {out.name}")
update_manifest()
PY

# Write COMPLETE if all scans done
pend=$("$PY" - "$ROOT" <<'PY'
import sys
from pathlib import Path
ROOT=Path(sys.argv[1])
sys.path.insert(0,str(ROOT/"scripts"))
from core_jyotisha_titles import TEXT_BOOKS_MD, md_name_for_pdf
SRC=Path("/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/newbooks/CoreJyothisha")
RAW=ROOT/"knowledge-graph/raw"
print(sum(1 for p in SRC.glob("*.pdf") if md_name_for_pdf(p) not in TEXT_BOOKS_MD and (not (RAW/md_name_for_pdf(p)).is_file() or (RAW/md_name_for_pdf(p)).stat().st_size<10000)))
PY
)
if [[ "$pend" -eq 0 ]]; then
  log "ALL 14 SCANS DONE"
  touch "$ROOT/knowledge-graph/ingest-logs/gcp-ocr-complete.marker"
  touch "$ROOT/knowledge-graph/ingest-logs/COMPLETE.md"
fi
log "BLAST FINISHED pending=$pend"
