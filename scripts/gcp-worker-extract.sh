#!/usr/bin/env bash
# Phase 2 on GCP VM: markdown → DeepSeek graph cache → GCS.
# Invoked by startup script or manually after OCR.
set -euo pipefail
exec >> /var/log/vedicastro-extract.log 2>&1

BUCKET="${BUCKET:-$(curl -sf -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/bucket)}"
WORKDIR="${WORKDIR:-/opt/vedicastro-worker}"
OCR_OUT="${OCR_OUT:-/opt/vedicastro-ocr/out}"
CONCURRENCY="${DEEPSEEK_CONCURRENCY:-10}"

echo "=== vedicastro extract $(date -u) bucket=$BUCKET ==="

export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq python3-venv python3-pip >/dev/null 2>&1 || true

mkdir -p "$WORKDIR"
cd "$WORKDIR"

if [[ ! -f graphify/.installed ]]; then
  echo "fetching worker bundle..."
  gsutil cp "gs://${BUCKET}/worker/graphify.tgz" "gs://${BUCKET}/worker/vedicastro-worker.tgz" .
  tar -xzf graphify.tgz
  rm -rf repo && mkdir repo && tar -xzf vedicastro-worker.tgz -C .
  touch graphify/.installed
fi

gsutil cp "gs://${BUCKET}/secrets/ingest.env" "$WORKDIR/ingest.env" 2>/dev/null || true
if [[ -f "$WORKDIR/ingest.env" ]]; then
  # shellcheck disable=SC1091
  set -a && source "$WORKDIR/ingest.env" && set +a
fi

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "error: DEEPSEEK_API_KEY missing — run gcp-secrets-upload.sh locally"
  exit 1
fi

python3 -m venv "$WORKDIR/venv"
# shellcheck disable=SC1091
source "$WORKDIR/venv/bin/activate"
pip install -q --upgrade pip openai

export GRAPHIFY_SITE="$WORKDIR/graphify"
REPO="$WORKDIR/repo"
RAW="$REPO/knowledge-graph/raw"
mkdir -p "$RAW"

echo "mapping OCR markdown → raw/..."
python3 - "$REPO" "$OCR_OUT" <<'PY'
import sys
from pathlib import Path
REPO, OCR_OUT = Path(sys.argv[1]), Path(sys.argv[2])
RAW = REPO / "knowledge-graph" / "raw"
sys.path.insert(0, str(REPO / "scripts"))
from core_jyotisha_titles import TITLE_MAP, md_name_for_pdf
from graph_extract_common import slugify_title

SOURCE_STEMS = {pdf_stem: md_name_for_pdf(Path(pdf_stem + ".pdf")) for pdf_stem in TITLE_MAP}

def canon(stem: str) -> str:
    if stem in TITLE_MAP:
        return TITLE_MAP[stem] + ".md"
    for pdf_stem in TITLE_MAP:
        if slugify_title(pdf_stem) == stem:
            return TITLE_MAP[pdf_stem] + ".md"
    return stem + ".md" if not stem.endswith(".md") else stem

for f in sorted(OCR_OUT.glob("*.md")):
    name = canon(f.stem)
    dest = RAW / name
    data = f.read_bytes()
    if not dest.is_file() or dest.read_bytes() != data:
        dest.write_bytes(data)
        print(f"  raw/{name} ({len(data)} bytes)")
PY

cd "$REPO"
echo "deepseek extract concurrency=$CONCURRENCY"
python3 scripts/deepseek-graph-extract.py run --max-concurrency "$CONCURRENCY"

echo "uploading graph artifacts to GCS..."
gsutil -m rsync -r "$REPO/knowledge-graph/graphify-out/cache/deepseek/" \
  "gs://${BUCKET}/graph-cache/deepseek/"
gsutil cp "$REPO/knowledge-graph/graphify-out/graph-deepseek.json" \
  "gs://${BUCKET}/graphs/graph-deepseek.json" 2>/dev/null || true
gsutil cp "$REPO/knowledge-graph/graphify-out/batch-deepseek/last-run.json" \
  "gs://${BUCKET}/graphs/deepseek-last-run.json" 2>/dev/null || true

echo "=== EXTRACT DONE $(date -u) ==="
