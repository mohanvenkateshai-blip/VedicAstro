#!/usr/bin/env bash
# Deploy extract phase to a running GCP VM (OCR may still be in progress).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ZONE="${GCP_ZONE:-us-central1-a}"
VM_NAME="${GCP_VM_NAME:-vedicastro-ocr}"
BUCKET="${GCP_BUCKET:-united-skyline-500618-t0-vedicastro-corpus}"

echo "=== Ensure worker bundle + secrets in GCS ==="
bash "$ROOT/scripts/gcp-bundle-worker.sh"
bash "$ROOT/scripts/gcp-secrets-upload.sh"

echo "=== Deploy extract watcher to $VM_NAME ==="
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --quiet <<REMOTE
set -euo pipefail
sudo mkdir -p /opt/vedicastro-worker
sudo gsutil -m cp gs://${BUCKET}/worker/graphify.tgz gs://${BUCKET}/worker/vedicastro-worker.tgz /tmp/
sudo tar -xzf /tmp/vedicastro-worker.tgz -C /opt/vedicastro-worker/
sudo tar -xzf /tmp/graphify.tgz -C /opt/vedicastro-worker/
sudo cp /opt/vedicastro-worker/repo/scripts/gcp-worker-extract.sh /opt/vedicastro-worker-extract.sh
sudo chmod +x /opt/vedicastro-worker-extract.sh

# Wait for OCR to finish, then run extract once
sudo tee /opt/vedicastro-extract-wait.sh >/dev/null <<WAIT
#!/bin/bash
exec >>/var/log/vedicastro-extract.log 2>&1
echo "extract-wait: polling for OCR completion..."
while pgrep -f marker_single >/dev/null 2>&1; do sleep 120; done
for _ in \$(seq 1 30); do
  grep -q "OCR DONE" /var/log/vedicastro-ocr.log 2>/dev/null && break
  pgrep -f marker_single >/dev/null 2>&1 && sleep 120 && continue
  sleep 60
done
export BUCKET=${BUCKET}
export OCR_OUT=/opt/vedicastro-ocr/out
bash /opt/vedicastro-worker-extract.sh
WAIT
sudo chmod +x /opt/vedicastro-extract-wait.sh

if pgrep -f vedicastro-extract-wait >/dev/null; then
  echo "extract watcher already running"
else
  sudo nohup bash /opt/vedicastro-extract-wait.sh </dev/null >/dev/null 2>&1 &
  echo "extract watcher started pid=\$!"
fi
REMOTE

echo "✓ deploy complete — tail extract log:"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE --command='tail -f /var/log/vedicastro-extract.log'"
