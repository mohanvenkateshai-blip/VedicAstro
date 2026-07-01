#!/bin/bash
# Verification Gate - Pre-commit / CI gate
# Runs: CVCE pytest golden, portal ci (lint/typecheck/build), structured verify --strict
# Blocks (non-zero exit) on any failure.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "=== Verification Gate starting from $ROOT_DIR ==="

# 1. CVCE pytest (golden tests)
echo ""
echo ">>> [1/3] CVCE pytest (cvce/tests/golden/)"
pushd "$ROOT_DIR/cvce" >/dev/null
python -m pytest tests/golden/ -q --tb=line
popd >/dev/null
echo "CVCE golden: OK"

# 2. Portal checks (use existing ci: lint + typecheck + build)
echo ""
echo ">>> [2/3] Portal checks (npm ci in portal/)"
pushd "$ROOT_DIR/portal" >/dev/null
npm run ci
popd >/dev/null
echo "Portal checks: OK"

# 3. Structured verify --strict
echo ""
echo ">>> [3/3] Structured books verify --strict"
python "$ROOT_DIR/scripts/verify_structured_books.py" --strict
echo "Structured verify: OK"

echo ""
echo "✅ Verification Gate PASSED - all checks successful"
exit 0