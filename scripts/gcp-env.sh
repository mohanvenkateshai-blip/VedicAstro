# Source from all ingest/GCP scripts. launchd has no Homebrew PATH.
export PATH="/opt/homebrew/bin:/opt/homebrew/share/google-cloud-sdk/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"
export CLOUDSDK_PYTHON="${CLOUDSDK_PYTHON:-/opt/homebrew/bin/python3}"
export GCP_PROJECT="${GCP_PROJECT:-united-skyline-500618-t0}"
export GCP_BUCKET="${GCP_BUCKET:-united-skyline-500618-t0-vedicastro-corpus}"
export GCP_ZONE="${GCP_ZONE:-us-central1-a}"
export PANCHANG_VENV="${PANCHANG_VENV:-/Users/ganesha/Projects/04-UX-Practice/Panchang/.venv}"
