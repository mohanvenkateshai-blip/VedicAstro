#!/usr/bin/env bash
# Sequential Marker OCR queue: priority PDFs first, then all remaining scans.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PANCHANG_VENV:-/Users/ganesha/Projects/04-UX-Practice/Panchang/.venv}/bin/python"
[[ -x "$PY" ]] || PY=python3
MARKER="$ROOT/scripts/marker-ocr.py"
EXTRA=()
for arg in "$@"; do
  [[ "$arg" == "--force" ]] && EXTRA+=(--force)
done

echo "=== Marker OCR queue started $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

run_marker() {
  if ((${#EXTRA[@]})); then
    "$PY" "$MARKER" "$@" "${EXTRA[@]}"
  else
    "$PY" "$MARKER" "$@"
  fi
}

# Priority classics first
run_marker --queue \
  "2015.312156.Jataka-Parijata.pdf" \
  "saravaliofkalyan01kalyuoft.pdf" \
  "Vedanga Jyotisa Lagadha -  Kupanna Sastry , K.V.Sarma.pdf" \
  "Panangadu_Nambudhiri_-_Prasna_Marga_(Part_I).pdf"

# Remaining scans
run_marker --all-scans

echo "=== Marker OCR queue finished $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
