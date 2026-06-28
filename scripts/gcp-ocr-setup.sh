#!/usr/bin/env bash
# GCP OCR worker for CoreJyothisha scanned PDFs (Marker + Surya on T4).
#
# Prereqs:
#   brew install --cask google-cloud-sdk
#   gcloud auth login
#   gcloud config set project united-skyline-500618-t0
#
# Usage:
#   ./scripts/gcp-ocr-setup.sh          # bucket + upload PDFs
#   ./scripts/gcp-ocr-setup.sh --create-vm   # create Spot GPU VM
#   ./scripts/gcp-ocr-setup.sh --status      # VM + bucket status
#   ./scripts/gcp-ocr-download.sh       # pull markdown → knowledge-graph/raw/
#   ./scripts/gcp-bundle-worker.sh      # upload worker bundle to GCS
#   ./scripts/gcp-secrets-upload.sh     # upload API keys to GCS (private)
#   ./scripts/gcp-deploy-extract.sh     # deploy extract to running VM
#   ./scripts/gcp-sync-results.sh       # pull markdown + graph cache local

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/newbooks/CoreJyothisha"
PROJECT="${GCP_PROJECT:-united-skyline-500618-t0}"
REGION="${GCP_REGION:-us-central1}"
ZONE="${GCP_ZONE:-us-central1-a}"
VM_NAME="${GCP_VM_NAME:-vedicastro-ocr}"
BUCKET="${GCP_BUCKET:-${PROJECT}-vedicastro-corpus}"
MACHINE_TYPE="${GCP_MACHINE_TYPE:-n1-standard-4}"
GPU_TYPE="${GCP_GPU_TYPE:-nvidia-tesla-t4}"
GPU_COUNT="${GCP_GPU_COUNT:-1}"

CREATE_VM=false
STATUS_ONLY=false
CPU_ONLY=false
SKIP_UPLOAD=false
for arg in "$@"; do
  case "$arg" in
    --create-vm) CREATE_VM=true ;;
    --status) STATUS_ONLY=true ;;
    --cpu-only) CPU_ONLY=true ;;
    --skip-upload) SKIP_UPLOAD=true ;;
  esac
done

die() { echo "error: $*" >&2; exit 1; }
need_gcloud() {
  command -v gcloud >/dev/null || die "gcloud not found — open a new terminal after: brew install --cask google-cloud-sdk"
  gcloud auth list --filter=status:ACTIVE --format='value(account)' | grep -q . \
    || die "run: gcloud auth login"
}

if $STATUS_ONLY; then
  need_gcloud
  echo "project=$PROJECT region=$REGION zone=$ZONE"
  gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --format='get(status,networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null \
    || echo "VM: not found"
  gsutil ls "gs://${BUCKET}/" 2>/dev/null | head -5 || echo "bucket: not found or empty"
  exit 0
fi

need_gcloud
gcloud config set project "$PROJECT" >/dev/null

echo "=== Enable APIs ==="
gcloud services enable compute.googleapis.com storage.googleapis.com --quiet

echo "=== GCS bucket gs://${BUCKET} ==="
if ! gsutil ls -b "gs://${BUCKET}" >/dev/null 2>&1; then
  gsutil mb -l "$REGION" "gs://${BUCKET}"
fi

echo "=== Upload scanned PDFs ==="
if $SKIP_UPLOAD; then
  echo "(skipped — PDFs already in gs://${BUCKET}/pdfs/CoreJyothisha/)"
else
  gsutil -m rsync -r "$SOURCE" "gs://${BUCKET}/pdfs/CoreJyothisha/"
fi

if ! $CREATE_VM; then
  echo ""
  echo "✓ PDFs uploaded. Next:"
  echo "  ./scripts/gcp-ocr-setup.sh --create-vm --skip-upload"
  exit 0
fi

STARTUP="$ROOT/scripts/gcp-ocr-startup.sh"
[[ -f "$STARTUP" ]] || die "missing $STARTUP"

echo "=== Create Spot VM: $VM_NAME ==="
if gcloud compute instances describe "$VM_NAME" --zone="$ZONE" >/dev/null 2>&1; then
  echo "VM already exists — delete first or set GCP_VM_NAME"
  gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --format='get(status)'
  exit 0
fi

TORCH_DEV="cpu"
CREATE_ARGS=(
  --zone="$ZONE"
  --machine-type="${GCP_MACHINE_TYPE:-n1-highcpu-16}"
  --provisioning-model=SPOT
  --instance-termination-action=STOP
  --boot-disk-size=100GB
  --boot-disk-type=pd-balanced
  --image-family=ubuntu-2204-lts
  --image-project=ubuntu-os-cloud
  --scopes=storage-full
  --metadata-from-file startup-script="$STARTUP"
  --metadata "bucket=${BUCKET},project=${PROJECT},torch_device=${TORCH_DEV}"
)

if ! $CPU_ONLY; then
  TORCH_DEV="cuda"
  CREATE_ARGS=(
    --zone="$ZONE"
    --machine-type="${GCP_MACHINE_TYPE:-n1-standard-4}"
    --accelerator="type=${GPU_TYPE},count=${GPU_COUNT}"
    --maintenance-policy=TERMINATE
    --provisioning-model=SPOT
    --instance-termination-action=STOP
    --boot-disk-size=100GB
    --boot-disk-type=pd-balanced
    --image-family=ubuntu-2204-lts
    --image-project=ubuntu-os-cloud
    --scopes=storage-full
    --metadata-from-file startup-script="$STARTUP"
    --metadata "bucket=${BUCKET},project=${PROJECT},torch_device=${TORCH_DEV}"
  )
fi

if ! $CPU_ONLY; then
  if ! gcloud compute instances create "$VM_NAME" "${CREATE_ARGS[@]}" 2>/tmp/gcp-vm-create.err; then
    if grep -q "GPUS_ALL_REGIONS\|QUOTA\|gpu" /tmp/gcp-vm-create.err 2>/dev/null; then
      echo "GPU quota unavailable — falling back to CPU Spot VM (slower but works)"
      TORCH_DEV="cpu"
      CREATE_ARGS=(
        --zone="$ZONE"
        --machine-type=n1-highcpu-16
        --provisioning-model=SPOT
        --instance-termination-action=STOP
        --boot-disk-size=100GB
        --boot-disk-type=pd-balanced
        --image-family=ubuntu-2204-lts
        --image-project=ubuntu-os-cloud
        --scopes=storage-full
        --metadata-from-file startup-script="$STARTUP"
        --metadata "bucket=${BUCKET},project=${PROJECT},torch_device=${TORCH_DEV}"
      )
      gcloud compute instances create "$VM_NAME" "${CREATE_ARGS[@]}"
    else
      cat /tmp/gcp-vm-create.err >&2
      exit 1
    fi
  fi
else
  gcloud compute instances create "$VM_NAME" "${CREATE_ARGS[@]}"
fi

IP=$(gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
echo ""
echo "✓ VM creating/running — external IP: ${IP:-pending}"
echo "  Monitor OCR log (after ~10 min boot):"
echo "    gcloud compute ssh $VM_NAME --zone=$ZONE --command='tail -f /var/log/vedicastro-ocr.log'"
echo "  When done, download markdown:"
echo "    ./scripts/gcp-ocr-download.sh"
