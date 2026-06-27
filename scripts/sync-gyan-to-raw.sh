#!/usr/bin/env bash
# Sync Panchang Gyan extracted_markdown → knowledge-graph/raw/ for graphify ingestion.
#
# Usage:
#   ./scripts/sync-gyan-to-raw.sh
#   ./scripts/sync-gyan-to-raw.sh --check   # list files missing from raw/

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GYAN="/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/extracted_markdown"
RAW="$ROOT/knowledge-graph/raw"
MANIFEST="$ROOT/knowledge-graph/corpus-manifest.json"

CHECK_ONLY=false
for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=true ;;
    -h|--help)
      sed -n '2,8p' "$0"
      exit 0
      ;;
  esac
done

if [[ ! -d "$GYAN" ]]; then
  echo "error: Gyan corpus not found at $GYAN" >&2
  exit 1
fi

mkdir -p "$RAW"

copied=0
skipped=0
missing=()

while IFS= read -r -d '' src; do
  base="$(basename "$src")"
  dst="$RAW/$base"
  if [[ -f "$dst" ]] && cmp -s "$src" "$dst" 2>/dev/null; then
    ((skipped++)) || true
    continue
  fi
  if $CHECK_ONLY; then
    missing+=("$base")
    continue
  fi
  cp "$src" "$dst"
  echo "→ $base"
  ((copied++)) || true
done < <(find "$GYAN" -name '*.md' -not -path '*/extracted_texts/*' -print0)

if $CHECK_ONLY; then
  if ((${#missing[@]})); then
    echo "Missing or changed in raw/: ${#missing[@]} files"
    printf '  %s\n' "${missing[@]}"
    exit 1
  fi
  echo "check: all Gyan markdown files present in raw/"
  exit 0
fi

# Write corpus manifest for audit trail
python3 - "$RAW" "$MANIFEST" <<'PY'
import json, hashlib, sys
from pathlib import Path
raw = Path(sys.argv[1])
manifest = Path(sys.argv[2])
files = {}
for p in sorted(raw.glob("*.md")):
    data = p.read_bytes()
    files[p.name] = {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest()[:16],
        "path": f"raw/{p.name}",
    }
manifest.write_text(json.dumps({"sources": files, "count": len(files)}, indent=2) + "\n")
print(f"manifest: {len(files)} sources → {manifest}")
PY

echo "✓ synced $copied new/updated, $skipped unchanged ($(ls -1 "$RAW"/*.md 2>/dev/null | wc -l | tr -d ' ') total in raw/)"
