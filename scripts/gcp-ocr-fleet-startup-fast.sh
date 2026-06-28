#!/usr/bin/env bash
# Fast fleet worker — pymupdf + Tesseract (minutes to install, hours not days per book).
set -euo pipefail
exec > /var/log/vedicastro-ocr.log 2>&1

meta() {
  curl -sf -H 'Metadata-Flavor: Google' \
    "http://metadata.google.internal/computeMetadata/v1/instance/attributes/$1" || echo ""
}

BUCKET="$(meta bucket)"
PDF_STEMS="$(meta pdf_stems)"
WORKER_ID="$(meta worker_id)"

echo "=== fast fleet worker $WORKER_ID $(date -u) ==="

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3-pip python3-venv tesseract-ocr poppler-utils

WORKDIR=/opt/vedicastro-fast
mkdir -p "$WORKDIR"
python3 -m venv "$WORKDIR/venv"
# shellcheck disable=SC1091
source "$WORKDIR/venv/bin/activate"
pip install -q --upgrade pip pymupdf pytesseract pdf2image pillow

gsutil -m cp "gs://${BUCKET}/worker/gcp-fast-pdf-to-md.py" "$WORKDIR/" 2>/dev/null || true
gsutil -m cp "gs://${BUCKET}/worker/gcp-worker-extract.sh" "$WORKDIR/" 2>/dev/null || true

PDF_DIR="$WORKDIR/pdfs"
OUT_DIR="$WORKDIR/out"
mkdir -p "$PDF_DIR" "$OUT_DIR"
gsutil -m rsync -r "gs://${BUCKET}/pdfs/CoreJyothisha/" "$PDF_DIR/"

IFS='|' read -ra STEMS <<< "$PDF_STEMS"
for stem in "${STEMS[@]}"; do
  [[ -n "$stem" ]] || continue
  pdf="$(find "$PDF_DIR" -iname "${stem}.pdf" | head -1)"
  [[ -f "$pdf" ]] || { echo "missing: $stem"; continue; }
  safe="$(echo "$stem" | sed 's/[^a-zA-Z0-9._-]/_/g' | sed 's/__*/_/g')"
  md="${OUT_DIR}/${safe}.md"
  if gsutil -q stat "gs://${BUCKET}/markdown/${safe}.md" 2>/dev/null; then
    echo "skip (gcs): $stem"
    continue
  fi
  echo "convert: $stem"
  python3 "$WORKDIR/gcp-fast-pdf-to-md.py" "$pdf" "$md" --workers 6 || echo "warn: low yield $stem"
  [[ -f "$md" ]] && gsutil -q cp "$md" "gs://${BUCKET}/markdown/$(basename "$md")"
done

echo "=== OCR DONE worker=$WORKER_ID $(date -u) ==="

if [[ "$WORKER_ID" == "0" ]]; then
  (
    sleep 120
    while true; do
      n="$(gsutil ls "gs://${BUCKET}/markdown/" 2>/dev/null | grep -c '\.md$' || true)"
      echo "markdown in GCS: $n"
      [[ "$n" -ge 20 ]] && break
      sleep 300
    done
    gsutil -m rsync -r "gs://${BUCKET}/markdown/" "$OUT_DIR/"
    gsutil cp "gs://${BUCKET}/worker/vedicastro-worker.tgz" /tmp/vw.tgz
    gsutil cp "gs://${BUCKET}/worker/graphify.tgz" /tmp/gf.tgz
    mkdir -p /opt/vedicastro-worker
    tar -xzf /tmp/vw.tgz -C /opt/vedicastro-worker/
    tar -xzf /tmp/gf.tgz -C /opt/vedicastro-worker/
    export BUCKET OCR_OUT="$OUT_DIR"
    bash /opt/vedicastro-worker/repo/scripts/gcp-worker-extract.sh
  ) >>/var/log/vedicastro-extract.log 2>&1 &
fi
