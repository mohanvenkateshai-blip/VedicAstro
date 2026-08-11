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

# B-16 graph version gate (fails only when GRAPH_VERSION is set and mismatches)
if [ -n "${GRAPH_VERSION:-}" ] || [ "${GRAPH_VERSION_REQUIRED:-}" = "1" ]; then
  export GRAPH_JSON_PATH="${GRAPH_JSON_PATH:-$(pwd)/graph_rag/graph.json}"
  .venv/bin/python -c "from app.graph_version_gate import enforce_at_startup; enforce_at_startup(strict=True)" \
    || { echo "ERROR: graph version gate failed — refusing to start with stale rules"; exit 1; }
fi

echo "Starting CVCE on http://localhost:${CVCE_PORT:-8400} ..."
.venv/bin/uvicorn app.server:app --host 127.0.0.1 --port "${CVCE_PORT:-8400}" --reload
