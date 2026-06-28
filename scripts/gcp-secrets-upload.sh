#!/usr/bin/env bash
# Upload API secrets for GCP worker (private GCS object — not committed).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${GCP_PROJECT:-united-skyline-500618-t0}"
BUCKET="${GCP_BUCKET:-${PROJECT}-vedicastro-corpus}"
ENV_LOCAL="$ROOT/portal/.env.local"
STAGING="$(mktemp)"
trap 'rm -f "$STAGING"' EXIT

[[ -f "$ENV_LOCAL" ]] || { echo "error: missing $ENV_LOCAL" >&2; exit 1; }

python3 - "$ENV_LOCAL" "$STAGING" <<'PY'
import sys
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
keys = ("DEEPSEEK_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")
found = {}
for line in src.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    k, v = k.strip(), v.strip().strip('"').strip("'")
    if k in keys and v:
        found[k] = v
if "DEEPSEEK_API_KEY" not in found:
    sys.exit("error: DEEPSEEK_API_KEY not in portal/.env.local")
lines = [f'{k}="{v}"' for k, v in found.items()]
dst.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"packed {len(found)} keys (DEEPSEEK required)")
PY

gsutil cp "$STAGING" "gs://${BUCKET}/secrets/ingest.env"
gsutil acl ch -u "$(gcloud config get-value account 2>/dev/null)":O "gs://${BUCKET}/secrets/ingest.env" 2>/dev/null || true
echo "✓ uploaded gs://${BUCKET}/secrets/ingest.env"
