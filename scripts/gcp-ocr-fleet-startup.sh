#!/usr/bin/env bash
# Fleet worker — OCR only assigned PDF stems, upload markdown, optional extract if last worker.
set -euo pipefail
exec > /var/log/vedicastro-ocr.log 2>&1

meta() {
  curl -sf -H 'Metadata-Flavor: Google' \
    "http://metadata.google.internal/computeMetadata/v1/instance/attributes/$1" || echo ""
}

BUCKET="$(meta bucket)"
PROJECT="$(meta project)"
TORCH_DEVICE="$(meta torch_device)"
PDF_STEMS="$(meta pdf_stems)"
WORKER_ID="$(meta worker_id)"

echo "=== fleet worker $WORKER_ID $(date -u) stems=$PDF_STEMS ==="

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3-pip python3-venv git rsync

OCR_ROOT=/opt/vedicastro-ocr
python3 -m venv "$OCR_ROOT/venv"
# shellcheck disable=SC1091
source "$OCR_ROOT/venv/bin/activate"
pip install -q --upgrade pip marker-pdf pymupdf

export TORCH_DEVICE="${TORCH_DEVICE:-cpu}"
PDF_DIR="$OCR_ROOT/pdfs"
OUT_DIR="$OCR_ROOT/out"
mkdir -p "$PDF_DIR" "$OUT_DIR"

gsutil -m rsync -r "gs://${BUCKET}/pdfs/CoreJyothisha/" "$PDF_DIR/"

IFS='|' read -ra STEMS <<< "$PDF_STEMS"
for stem in "${STEMS[@]}"; do
  pdf="$(find "$PDF_DIR" -name "${stem}.pdf" | head -1)"
  [[ -f "$pdf" ]] || { echo "missing pdf for stem=$stem"; continue; }
  safe="$(echo "$stem" | sed 's/[^a-zA-Z0-9._-]/_/g' | sed 's/__*/_/g')"
  md="${OUT_DIR}/${safe}.md"
  if [[ -f "$md" ]] && [[ "$(wc -c <"$md")" -gt 1000 ]]; then
    echo "skip $stem"
    gsutil -q cp "$md" "gs://${BUCKET}/markdown/$(basename "$md")" 2>/dev/null || true
    continue
  fi
  echo "marker: $stem"
  marker_single "$pdf" --output_dir "${OUT_DIR}/.work/${safe}" --output_format markdown
  found="$(find "${OUT_DIR}/.work/${safe}" -name '*.md' | head -1)"
  if [[ -n "$found" ]]; then
    cp "$found" "$md"
    gsutil -q cp "$md" "gs://${BUCKET}/markdown/$(basename "$md")"
  fi
done

gsutil -m rsync -r "$OUT_DIR/" "gs://${BUCKET}/markdown/"
echo "=== OCR DONE worker=$WORKER_ID $(date -u) ==="

# Worker 0 runs extract after all OCR (polls GCS for expected count)
if [[ "$WORKER_ID" == "0" ]]; then
  gsutil cp "gs://${BUCKET}/worker/vedicastro-worker.tgz" /tmp/vedicastro-worker.tgz
  gsutil cp "gs://${BUCKET}/worker/graphify.tgz" /tmp/graphify.tgz
  mkdir -p /opt/vedicastro-worker
  tar -xzf /tmp/vedicastro-worker.tgz -C /opt/vedicastro-worker/
  tar -xzf /tmp/graphify.tgz -C /opt/vedicastro-worker/
  cp /opt/vedicastro-worker/repo/scripts/gcp-worker-extract.sh /opt/vedicastro-worker-extract.sh
  chmod +x /opt/vedicastro-worker-extract.sh
  (
    echo "extract-wait: fleet mode — waiting for markdown in GCS..."
  sleep 300
  while true; do
    n="$(gsutil ls "gs://${BUCKET}/markdown/" 2>/dev/null | grep -c '\.md$' || true)"
    echo "gcs markdown count=$n"
    [[ "$n" -ge 14 ]] && break
    sleep 600
  done
  gsutil -m rsync -r "gs://${BUCKET}/markdown/" "$OCR_ROOT/out/"
  export BUCKET OCR_OUT="$OCR_ROOT/out"
  bash /opt/vedicastro-worker-extract.sh
  ) >>/var/log/vedicastro-extract.log 2>&1 &
fi

echo "=== ALL DONE worker=$WORKER_ID ==="
