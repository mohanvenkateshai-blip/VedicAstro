#!/usr/bin/env bash
# Package scripts + graph base + graphify + text-book raw → GCS worker bundle.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${GCP_PROJECT:-united-skyline-500618-t0}"
BUCKET="${GCP_BUCKET:-${PROJECT}-vedicastro-corpus}"
PANCHANG_VENV="${PANCHANG_VENV:-/Users/ganesha/Projects/04-UX-Practice/Panchang/.venv}"
GRAPHIFY_SRC="$PANCHANG_VENV/lib/python3.14/site-packages/graphify"
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

die() { echo "error: $*" >&2; exit 1; }
[[ -d "$GRAPHIFY_SRC" ]] || die "graphify not found at $GRAPHIFY_SRC"

echo "=== Bundle worker → gs://${BUCKET}/worker/ ==="
mkdir -p "$STAGING/repo/scripts" "$STAGING/repo/knowledge-graph/graphify-out/cache/deepseek"
mkdir -p "$STAGING/repo/knowledge-graph/raw"

cp "$ROOT/scripts/deepseek-graph-extract.py" \
   "$ROOT/scripts/graph_extract_common.py" \
   "$ROOT/scripts/core_jyotisha_titles.py" \
   "$ROOT/scripts/gcp-worker-extract.sh" \
   "$STAGING/repo/scripts/"

cp "$ROOT/knowledge-graph/graphify-out/graph.json" "$STAGING/repo/knowledge-graph/graphify-out/"
if [[ -d "$ROOT/knowledge-graph/graphify-out/cache/deepseek" ]]; then
  cp -r "$ROOT/knowledge-graph/graphify-out/cache/deepseek/." \
    "$STAGING/repo/knowledge-graph/graphify-out/cache/deepseek/" 2>/dev/null || true
fi

# Text books already converted locally
for md in Brihat_Jataka.md Brihat_Parasara_Hora_Sastra_Vol_2.md Bhrigu_Samhita_TMRao.md \
          Laghu_Parashari.md Prasna_Marga_Part_2.md Uttara_Kalamrita.md; do
  [[ -f "$ROOT/knowledge-graph/raw/$md" ]] && cp "$ROOT/knowledge-graph/raw/$md" "$STAGING/repo/knowledge-graph/raw/"
done

tar -czf "$STAGING/graphify.tgz" -C "$PANCHANG_VENV/lib/python3.14/site-packages" \
  --exclude='graphify/skills' graphify

tar -czf "$STAGING/vedicastro-worker.tgz" -C "$STAGING" repo

gsutil -m cp "$STAGING/graphify.tgz" "$STAGING/vedicastro-worker.tgz" "gs://${BUCKET}/worker/"
echo "✓ worker bundle uploaded"
echo "  next: ./scripts/gcp-secrets-upload.sh"
