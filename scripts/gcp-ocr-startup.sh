#!/usr/bin/env bash
# Runs on GCE VM at boot — OCR → GCS markdown → DeepSeek extract → GCS graph cache.
set -euo pipefail
exec > /var/log/vedicastro-ocr.log 2>&1

BUCKET="$(curl -sf -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/bucket)"
PROJECT="$(curl -sf -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/project)"
TORCH_DEVICE="$(curl -sf -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/torch_device || echo cpu)"

echo "=== vedicastro worker $(date -u) bucket=$BUCKET device=$TORCH_DEVICE ==="

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3-pip python3-venv git rsync

if [[ "$TORCH_DEVICE" == "cuda" ]]; then
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    apt-get install -y -qq ubuntu-drivers-common
    ubuntu-drivers install --gpgpu -q || true
  fi
fi

OCR_ROOT=/opt/vedicastro-ocr
mkdir -p "$OCR_ROOT"
python3 -m venv "$OCR_ROOT/venv"
# shellcheck disable=SC1091
source "$OCR_ROOT/venv/bin/activate"
pip install -q --upgrade pip
pip install -q marker-pdf pymupdf

export TORCH_DEVICE="${TORCH_DEVICE:-cpu}"
PDF_DIR="$OCR_ROOT/pdfs"
OUT_DIR="$OCR_ROOT/out"
mkdir -p "$PDF_DIR" "$OUT_DIR"

gsutil -m rsync -r "gs://${BUCKET}/pdfs/CoreJyothisha/" "$PDF_DIR/"

process_pdf() {
  local pdf="$1"
  local base stem md found
  base="$(basename "$pdf" .pdf)"
  stem="$(echo "$base" | sed 's/[^a-zA-Z0-9._-]/_/g' | sed 's/__*/_/g')"
  md="${OUT_DIR}/${stem}.md"
  if [[ -f "$md" ]] && [[ "$(wc -c <"$md")" -gt 1000 ]]; then
    echo "skip $base"
    return 0
  fi
  echo "marker: $base"
  marker_single "$pdf" --output_dir "${OUT_DIR}/.work/${stem}" --output_format markdown
  found="$(find "${OUT_DIR}/.work/${stem}" -name '*.md' | head -1)"
  if [[ -n "$found" ]]; then
    cp "$found" "$md"
    gsutil -q cp "$md" "gs://${BUCKET}/markdown/$(basename "$md")" || true
  fi
}

export -f process_pdf
export OUT_DIR PDF_DIR BUCKET
find "$PDF_DIR" -name '*.pdf' | sort | while read -r pdf; do
  process_pdf "$pdf" || echo "failed: $pdf"
done

gsutil -m rsync -r "$OUT_DIR/" "gs://${BUCKET}/markdown/"
echo "=== OCR DONE $(date -u) ==="

gsutil cp "gs://${BUCKET}/worker/vedicastro-worker.tgz" /tmp/vedicastro-worker.tgz
gsutil cp "gs://${BUCKET}/worker/graphify.tgz" /tmp/graphify.tgz
mkdir -p /opt/vedicastro-worker
tar -xzf /tmp/vedicastro-worker.tgz -C /opt/vedicastro-worker/
tar -xzf /tmp/graphify.tgz -C /opt/vedicastro-worker/
cp /opt/vedicastro-worker/repo/scripts/gcp-worker-extract.sh /opt/vedicastro-worker-extract.sh
chmod +x /opt/vedicastro-worker-extract.sh
export BUCKET OCR_OUT="$OUT_DIR"
bash /opt/vedicastro-worker-extract.sh 2>/var/log/vedicastro-extract.log

echo "=== ALL DONE $(date -u) ==="
gsutil ls "gs://${BUCKET}/graphs/" 2>/dev/null | head -10
