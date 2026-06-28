#!/usr/bin/env bash
# Core Jyotisha ingest status — run manually or via launchd every 15 min.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/gcp-env.sh"
PY="$PANCHANG_VENV/bin/python"
LOG="$ROOT/knowledge-graph/ingest-logs/status-report.log"
TS="$(date '+%Y-%m-%d %H:%M:%S %Z')"

mkdir -p "$ROOT/knowledge-graph/ingest-logs"

{
  echo ""
  echo "════════════════════════════════════════════════════════════"
  echo "INGEST STATUS — $TS"
  echo "════════════════════════════════════════════════════════════"

  echo ""
  echo "## Graphs"
  "$PY" -c "
import json
from pathlib import Path
p = Path('$ROOT/knowledge-graph/graphify-out')
for f in ('graph.json', 'graph-deepseek.json', 'graph-core-jyotisha.json'):
    fp = p / f
    if fp.is_file():
        g = json.loads(fp.read_text())
        print(f'  {f}: {len(g[\"nodes\"])} nodes, {len(g.get(\"links\", []))} links')
"

  echo ""
  echo "## Books"
  "$PY" - "$ROOT" <<'PY'
import sys
from pathlib import Path
ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "scripts"))
from core_jyotisha_titles import TEXT_BOOKS_MD, md_name_for_pdf

SRC = Path("/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/newbooks/CoreJyothisha")
RAW = ROOT / "knowledge-graph/raw"
text_ok = sum(1 for m in TEXT_BOOKS_MD if (RAW / m).is_file())
scan_ready, scan_pending = [], []
for pdf in sorted(SRC.glob("*.pdf")):
    md = md_name_for_pdf(pdf)
    if md in TEXT_BOOKS_MD:
        continue
    f = RAW / md
    if f.is_file() and f.stat().st_size > 10000:
        scan_ready.append(md)
    else:
        scan_pending.append(md)
print(f"  Text books: {text_ok}/6")
print(f"  Scans OCR done: {len(scan_ready)}/14")
for m in scan_ready:
    print(f"    ✓ {m}")
print(f"  Scans pending: {len(scan_pending)}")
for m in scan_pending:
    print(f"    · {m}")
PY

  echo ""
  echo "## GCS"
  gcs_n="$(gsutil ls "gs://${GCP_BUCKET}/markdown/" 2>/dev/null | grep -c '\.md$' || echo 0)"
  graph_gcs="no"
  gsutil ls "gs://${GCP_BUCKET}/graphs/graph-deepseek.json" >/dev/null 2>&1 && graph_gcs="yes"
  echo "  markdown files: $gcs_n"
  echo "  graph-deepseek.json in GCS: $graph_gcs"

  echo ""
  echo "## Processes"
  ocr="$(pgrep -fc 'gcp-fast-pdf-to-md' 2>/dev/null || echo 0)"
  ds="$(pgrep -fc 'deepseek-graph-extract' 2>/dev/null || echo 0)"
  daemon="$(pgrep -fc 'pipeline-daemon' 2>/dev/null || echo 0)"
  watch="$(pgrep -fc 'gcp-ocr-watch' 2>/dev/null || echo 0)"
  echo "  OCR workers: $ocr"
  echo "  DeepSeek: $ds"
  echo "  pipeline-daemon: $daemon"
  echo "  gcp-sync-watch: $watch"

  echo ""
  echo "## GCP fleet"
  gcloud compute instances list --filter="name~'^vedicastro-ocr'" \
    --format="table(name,status)" 2>/dev/null || echo "  (gcloud unavailable)"

  echo ""
  echo "## Markers"
  for m in gcp-ocr-complete gcp-extract-complete; do
    f="$ROOT/knowledge-graph/ingest-logs/${m}.marker"
    [[ -f "$f" ]] && echo "  ✓ $m" || echo "  · $m (not set)"
  done
  [[ -f "$ROOT/knowledge-graph/ingest-logs/COMPLETE.md" ]] && echo "  ✓ COMPLETE.md" || echo "  · COMPLETE.md (not written)"

  echo ""
  echo "## Recent activity"
  tail -3 "$ROOT/knowledge-graph/ingest-logs/ocr-final.log" 2>/dev/null | sed 's/^/  /' || true
  tail -2 "$ROOT/knowledge-graph/ingest-logs/gcp-sync-watch.log" 2>/dev/null | sed 's/^/  /' || true
  tail -2 "$ROOT/knowledge-graph/ingest-logs/deepseek-ocr.log" 2>/dev/null | sed 's/^/  /' || true

} | tee -a "$LOG"
