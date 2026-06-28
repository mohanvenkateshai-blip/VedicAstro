#!/usr/bin/env bash
# Pull GCP worker outputs → local knowledge-graph (markdown, cache, merged graphs).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${GCP_PROJECT:-united-skyline-500618-t0}"
BUCKET="${GCP_BUCKET:-${PROJECT}-vedicastro-corpus}"
RAW="$ROOT/knowledge-graph/raw"
CACHE="$ROOT/knowledge-graph/graphify-out/cache/deepseek"
GRAPHS="$ROOT/knowledge-graph/graphify-out"
PY="${PANCHANG_VENV:-/Users/ganesha/Projects/04-UX-Practice/Panchang/.venv}/bin/python"
[[ -x "$PY" ]] || PY=python3

mkdir -p "$RAW" "$CACHE" "$GRAPHS"

echo "=== Sync from gs://${BUCKET}/ ==="

if gsutil ls "gs://${BUCKET}/markdown/" >/dev/null 2>&1; then
  bash "$ROOT/scripts/gcp-ocr-download.sh"
fi

if gsutil ls "gs://${BUCKET}/graph-cache/deepseek/" >/dev/null 2>&1; then
  echo "→ graph-cache/deepseek/"
  gsutil -m rsync -r "gs://${BUCKET}/graph-cache/deepseek/" "$CACHE/"
  n="$(find "$CACHE" -name '*.json' 2>/dev/null | wc -l | tr -d ' ')"
  echo "  $n cache files local"
fi

for obj in graph-deepseek.json deepseek-last-run.json graph-core-jyotisha.json; do
  if gsutil ls "gs://${BUCKET}/graphs/${obj}" >/dev/null 2>&1; then
    gsutil cp "gs://${BUCKET}/graphs/${obj}" "$GRAPHS/${obj}"
    echo "→ graphify-out/${obj}"
  fi
done

if [[ ! -f "$GRAPHS/graph-deepseek.json" ]] && [[ -n "$(ls -A "$CACHE" 2>/dev/null)" ]]; then
  echo "→ merge from cache"
  "$PY" "$ROOT/scripts/deepseek-graph-extract.py" merge
fi

"$PY" "$ROOT/scripts/ingest-core-jyotisha.py" manifest 2>/dev/null || true

if [[ "${SKIP_SUPABASE_SYNC:-}" != "1" ]] && [[ -f "$ROOT/scripts/supabase-corpus-sync.py" ]]; then
  echo "=== Supabase corpus vault ==="
  "$PY" "$ROOT/scripts/supabase-corpus-sync.py" --skip-gcp || echo "warn: supabase sync failed (run schema first?)"
fi

echo "✓ gcp-sync-results complete"
