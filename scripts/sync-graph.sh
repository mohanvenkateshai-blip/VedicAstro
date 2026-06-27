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
#   ./scripts/sync-graph.sh --grok         # also copy graph-grok.json (experimental)
#
# Usage:
#   ./scripts/sync-graph.sh           # copy + print stats
#   ./scripts/sync-graph.sh --check   # compare counts only, no copy
#   ./scripts/sync-graph.sh --deploy  # copy then fly deploy (cvce/)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/knowledge-graph/graphify-out/graph.json"
SRC_GROK="$ROOT/knowledge-graph/graphify-out/graph-grok.json"
SRC_GEMINI="$ROOT/knowledge-graph/graphify-out/graph-gemini.json"
SRC_GLM="$ROOT/knowledge-graph/graphify-out/graph-glm.json"
SRC_DEEPSEEK="$ROOT/knowledge-graph/graphify-out/graph-deepseek.json"
DST="$ROOT/cvce/graph_rag/graph.json"
DST_GROK="$ROOT/cvce/graph_rag/graph-grok.json"
DST_GEMINI="$ROOT/cvce/graph_rag/graph-gemini.json"
DST_GLM="$ROOT/cvce/graph_rag/graph-glm.json"
DST_DEEPSEEK="$ROOT/cvce/graph_rag/graph-deepseek.json"
STALE="$ROOT/cvce/data/graph.json"

CHECK_ONLY=false
DEPLOY=false
WITH_GROK=false
WITH_GEMINI=false
WITH_GLM=false
WITH_DEEPSEEK=false

for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=true ;;
    --deploy) DEPLOY=true ;;
    --grok) WITH_GROK=true ;;
    --gemini) WITH_GEMINI=true ;;
    --glm) WITH_GLM=true ;;
    --deepseek) WITH_DEEPSEEK=true ;;
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

if $WITH_GROK; then
  if [[ ! -f "$SRC_GROK" ]]; then
    echo "error: --grok requested but missing $SRC_GROK" >&2
    echo "  run: python3 scripts/build-graph-grok.py" >&2
    exit 1
  fi
  cp "$SRC_GROK" "$DST_GROK"
  echo "copied → $DST_GROK (grok line)"
  stats "$DST_GROK"
fi

if $WITH_GEMINI; then
  if [[ ! -f "$SRC_GEMINI" ]]; then
    echo "error: --gemini requested but missing $SRC_GEMINI" >&2
    echo "  run: python3 scripts/gemini-batch-graph-extract.py merge --output graph-gemini.json" >&2
    exit 1
  fi
  cp "$SRC_GEMINI" "$DST_GEMINI"
  echo "copied → $DST_GEMINI (gemini line)"
  stats "$DST_GEMINI"
fi

if $WITH_GLM; then
  if [[ ! -f "$SRC_GLM" ]]; then
    echo "error: --glm requested but missing $SRC_GLM" >&2
    echo "  run: python3 scripts/glm-batch-graph-extract.py merge" >&2
    exit 1
  fi
  cp "$SRC_GLM" "$DST_GLM"
  echo "copied → $DST_GLM (glm line)"
  stats "$DST_GLM"
fi

if $WITH_DEEPSEEK; then
  if [[ ! -f "$SRC_DEEPSEEK" ]]; then
    echo "error: --deepseek requested but missing $SRC_DEEPSEEK" >&2
    echo "  run: python3 scripts/deepseek-graph-extract.py run" >&2
    exit 1
  fi
  cp "$SRC_DEEPSEEK" "$DST_DEEPSEEK"
  echo "copied → $DST_DEEPSEEK (deepseek line)"
  stats "$DST_DEEPSEEK"
fi

if $DEPLOY; then
  echo "deploying CVCE (fly)…"
  (cd "$ROOT/cvce" && fly deploy --remote-only --ha=false)
  echo "verify: curl -s \$CVCE_BASE_URL/predict/health | jq .graph_rag"
  if $WITH_GROK; then
    echo "verify grok: curl -s \$CVCE_BASE_URL/predict/health/grok | jq ."
  fi
  if $WITH_GEMINI; then
    echo "verify gemini: curl -s \$CVCE_BASE_URL/predict/health/gemini | jq ."
  fi
  if $WITH_GLM; then
    echo "verify glm: curl -s \$CVCE_BASE_URL/predict/health/glm | jq ."
  fi
  if $WITH_DEEPSEEK; then
    echo "verify deepseek: curl -s \$CVCE_BASE_URL/predict/health/deepseek | jq ."
  fi
fi
