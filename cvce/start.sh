#!/bin/bash
# Local dev launcher for the CVCE. Run setup with:
#   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python patch_pyjhora.py
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Virtual environment (.venv) not found. Create it first:"
  echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python patch_pyjhora.py"
  exit 1
fi

[ -f .env ] || { [ -f .env.example ] && cp .env.example .env && echo "Created .env from .env.example"; }

echo "Starting CVCE on http://localhost:${CVCE_PORT:-8400} ..."
.venv/bin/uvicorn app.server:app --host 127.0.0.1 --port "${CVCE_PORT:-8400}" --reload
