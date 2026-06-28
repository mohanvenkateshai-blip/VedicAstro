#!/usr/bin/env bash
# Launch N parallel Spot VMs — each OCRs a slice of CoreJyothisha PDFs on GCP.
# Use when GPU quota is 0 but you want to use more CPU capacity.
#
# Usage:
#   ./scripts/gcp-ocr-fleet.sh --workers 7        # 7 VMs, ~2 PDFs each
#   ./scripts/gcp-ocr-fleet.sh --workers 7 --dry-run
#   ./scripts/gcp-ocr-fleet.sh --status
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${GCP_PROJECT:-united-skyline-500618-t0}"
REGION="${GCP_REGION:-us-central1}"
ZONE="${GCP_ZONE:-us-central1-a}"
BUCKET="${GCP_BUCKET:-${PROJECT}-vedicastro-corpus}"
WORKERS=3
MACHINE="${GCP_FLEET_MACHINE:-e2-highcpu-8}"
REPLACE=false
DRY_RUN=false
STATUS_ONLY=false

for arg in "$@"; do
  case "$arg" in
    --workers) shift; WORKERS="${1:-3}"; shift || true ;;
    --workers=*) WORKERS="${arg#*=}" ;;
    --machine-type) shift; MACHINE="${1:-e2-highcpu-8}"; shift || true ;;
    --machine-type=*) MACHINE="${arg#*=}" ;;
    --replace) REPLACE=true ;;
    --marker) FAST_MODE=false; FLEET_STARTUP="$ROOT/scripts/gcp-ocr-fleet-startup.sh" ;;
    --dry-run) DRY_RUN=true ;;
    --status) STATUS_ONLY=true ;;
  esac
done

STARTUP="$ROOT/scripts/gcp-ocr-startup.sh"
FLEET_STARTUP="$ROOT/scripts/gcp-ocr-fleet-startup-fast.sh"
FAST_MODE=true

if $STATUS_ONLY; then
  gcloud compute instances list --filter="name~'^vedicastro-ocr-'" --format='table(name,zone,status,machineType.basename())'
  echo ""
  gsutil ls "gs://${BUCKET}/markdown/" 2>/dev/null | grep -c '\.md$' || echo "0 markdown files"
  exit 0
fi

[[ -f "$STARTUP" ]] || { echo "error: missing $STARTUP" >&2; exit 1; }
command -v gcloud >/dev/null || { echo "error: gcloud not found" >&2; exit 1; }

echo "=== Fleet OCR: $WORKERS × $MACHINE (fast=${FAST_MODE}) → gs://${BUCKET}/ ==="
gsutil cp "$ROOT/scripts/gcp-fast-pdf-to-md.py" "gs://${BUCKET}/worker/gcp-fast-pdf-to-md.py" 2>/dev/null || true
bash "$ROOT/scripts/gcp-bundle-worker.sh" >/dev/null 2>&1 || true
bash "$ROOT/scripts/gcp-secrets-upload.sh" >/dev/null 2>&1 || true

if $REPLACE; then
  echo "stopping sequential worker vedicastro-ocr (free CPU quota for fleet)..."
  gcloud compute instances stop vedicastro-ocr --zone="$ZONE" --quiet 2>/dev/null || true
fi

# Pending = scan PDFs not yet in GCS markdown (exclude pymupdf text books)
PENDING=()
while IFS= read -r stem; do
  safe="$(echo "$stem" | sed 's/[^a-zA-Z0-9._-]/_/g' | sed 's/__*/_/g')"
  if gsutil -q stat "gs://${BUCKET}/markdown/${safe}.md" 2>/dev/null; then
    echo "done: $stem"
    continue
  fi
  # skip text-layer PDFs (already converted via pymupdf locally)
  case "$stem" in
    Varaha_Mihira_-_Brihat_Jataka|BPHS\ -\ 2\ RSanthanam|"Book. Bhrigu Samhita T.M.Rao_text"|"Laghu Parashari OPVerma"|"Kalidasa_-_Uttara_Kalamrita"|"Prasna Marga Part 2 by BV Raman") continue ;;
  esac
  PENDING+=("$stem")
done < <(gsutil ls "gs://${BUCKET}/pdfs/CoreJyothisha/*.pdf" 2>/dev/null | while read -r u; do basename "$u" .pdf; done | sort)

[[ ${#PENDING[@]} -gt 0 ]] || { echo "✓ all PDFs already in GCS markdown/"; exit 0; }
echo "Pending OCR: ${#PENDING[@]} PDFs — splitting across $WORKERS workers"

for ((w=0; w<WORKERS; w++)); do
  VM="vedicastro-ocr-${w}"
  slice=""
  for ((i=w; i<${#PENDING[@]}; i+=WORKERS)); do
    slice+="${PENDING[$i]},"
  done
  slice="${slice%,}"
  [[ -n "$slice" ]] || continue

  if gcloud compute instances describe "$VM" --zone="$ZONE" >/dev/null 2>&1; then
    if $REPLACE; then
      echo "delete $VM (--replace)"
      $DRY_RUN || gcloud compute instances delete "$VM" --zone="$ZONE" --quiet
    else
      echo "skip $VM (exists — use --replace)"
      continue
    fi
  fi

  echo "create $VM ← ${slice//,/, }"
  if $DRY_RUN; then
    continue
  fi

  META_DIR="$(mktemp -d)"
  echo "$slice" | tr ',' '\n' | grep -v '^$' | paste -sd'|' - >"$META_DIR/pdf_stems"
  echo "$w" >"$META_DIR/worker_id"
  echo "$BUCKET" >"$META_DIR/bucket"
  echo "$PROJECT" >"$META_DIR/project"
  echo "cpu" >"$META_DIR/torch_device"

  gcloud compute instances create "$VM" \
    --zone="$ZONE" \
    --machine-type="$MACHINE" \
    --provisioning-model=SPOT \
    --instance-termination-action=STOP \
    --boot-disk-size=100GB \
    --boot-disk-type=pd-balanced \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --scopes=storage-full \
    --metadata-from-file "startup-script=$FLEET_STARTUP,pdf_stems=$META_DIR/pdf_stems,worker_id=$META_DIR/worker_id,bucket=$META_DIR/bucket,project=$META_DIR/project,torch_device=$META_DIR/torch_device" \
    --quiet
  rm -rf "$META_DIR"
done

echo ""
echo "✓ fleet launched — monitor:"
echo "  ./scripts/gcp-ocr-fleet.sh --status"
echo "  gcloud compute ssh vedicastro-ocr-0 --zone=$ZONE --command='tail -f /var/log/vedicastro-ocr.log'"
