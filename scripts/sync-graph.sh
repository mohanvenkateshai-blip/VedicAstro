#!/usr/bin/env bash
# Sync graphify output → CVCE deploy bundle.
#
# Graphify builds offline:  knowledge-graph/graphify-out/graph.json
# CVCE loads at runtime:   cvce/graph_rag/graph.json  (gitignored; baked into Fly image)
#
# Full Gyan corpus pipeline:
#   ./scripts/sync-gyan-to-raw.sh          # Panchang/Gyan → knowledge-graph/raw/
#   python3 scripts/gyan-corpus-extract.py # merge corpus into graph.json
#   ./scripts/sync-graph.sh [--deploy]     # copy graph → cvce + optional Fly deploy
#
# Usage:
#   ./scripts/sync-graph.sh           # copy + print stats
#   ./scripts/sync-graph.sh --check   # compare counts only, no copy
#   ./scripts/sync-graph.sh --deploy  # copy then fly deploy (cvce/)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/knowledge-graph/graphify-out/graph.json"
DST="$ROOT/cvce/graph_rag/graph.json"
STALE="$ROOT/cvce/data/graph.json"

CHECK_ONLY=false
DEPLOY=false

for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=true ;;
    --deploy) DEPLOY=true ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg (try --help)" >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$SRC" ]]; then
  echo "error: source missing — run graphify on knowledge-graph/raw first" >&2
  echo "  expected: $SRC" >&2
  exit 1
fi

stats() {
  python3 - "$1" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text(encoding="utf-8"))
print(f"  nodes={len(d.get('nodes', []))} links={len(d.get('links', []))} hyperedges={len(d.get('hyperedges', []))}")
PY
}

echo "Graphify → CVCE sync"
echo "  source: $SRC"
stats "$SRC"

if [[ -f "$DST" ]]; then
  echo "  deploy: $DST (current)"
  stats "$DST"
fi

if [[ -f "$STALE" ]]; then
  echo "  note:   $STALE is unused by runtime — consider removing or re-syncing"
  stats "$STALE"
fi

if $CHECK_ONLY; then
  if [[ ! -f "$DST" ]]; then
    echo "check: deploy copy missing — run without --check to create"
    exit 1
  fi
  python3 - "$SRC" "$DST" <<'PY'
import json, sys
from pathlib import Path
def load(p):
    d = json.loads(Path(p).read_text(encoding="utf-8"))
    return len(d.get("nodes", [])), len(d.get("links", []))
s = load(sys.argv[1])
d = load(sys.argv[2])
if s == d:
    print("check: deploy copy matches graphify-out")
    sys.exit(0)
print(f"check: MISMATCH graphify-out {s[0]}n/{s[1]}l vs deploy {d[0]}n/{d[1]}l")
sys.exit(1)
PY
  exit $?
fi

mkdir -p "$(dirname "$DST")"
cp "$SRC" "$DST"
echo "copied → $DST"
stats "$DST"

if $DEPLOY; then
  echo "deploying CVCE (fly)…"
  (cd "$ROOT/cvce" && fly deploy --remote-only --ha=false)
  echo "verify: curl -s \$CVCE_BASE_URL/predict/health | jq .graph_rag"
fi
