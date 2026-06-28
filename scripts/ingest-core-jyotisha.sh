#!/usr/bin/env bash
# Wrapper for Core Jyotisha classical corpus ingestion.
#
# Usage:
#   ./scripts/ingest-core-jyotisha.sh list
#   ./scripts/ingest-core-jyotisha.sh convert          # text PDFs only (fast)
#   ./scripts/ingest-core-jyotisha.sh convert --ocr    # include scanned PDFs (slow)
#   ./scripts/ingest-core-jyotisha.sh extract --providers deepseek
#   ./scripts/ingest-core-jyotisha.sh merge
#   ./scripts/ingest-core-jyotisha.sh go              # parallel DeepSeek + Marker OCR
#   ./scripts/ingest-core-jyotisha.sh --concurrency 3 go

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PANCHANG_VENV:-/Users/ganesha/Projects/04-UX-Practice/Panchang/.venv}/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi
exec "$PY" "$ROOT/scripts/ingest-core-jyotisha.py" "$@"
