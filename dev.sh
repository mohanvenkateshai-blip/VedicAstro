#!/usr/bin/env bash
# VedicAstro local dev launcher — starts CVCE + Portal side-by-side.
# Usage: ./dev.sh
# See LOCAL_DEV.md for context and GA checklist.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
CVCE_DIR="$REPO_ROOT/cvce"
PORTAL_DIR="$REPO_ROOT/portal"

# Mirror the fly.toml env vars so local CVCE behaves identically to production
export CVCE_HOST=0.0.0.0
export CVCE_PORT=8400
export CVCE_DEFAULT_AYANAMSA=LAHIRI
export CVCE_VARGAS="1,2,3,4,7,9,10,12,16,24,30,60"
export CVCE_GRAPH_AS_RULES=1
export CVCE_ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"

cleanup() {
  echo ""
  echo "Shutting down..."
  kill "$CVCE_PID" "$PORTAL_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# ── CVCE ──────────────────────────────────────────────────────────────────────
echo "▶ Starting CVCE on :8400..."
cd "$CVCE_DIR"
source .venv/bin/activate
uvicorn app.server:app --host 0.0.0.0 --port 8400 --reload &
CVCE_PID=$!

# Wait up to 30s for CVCE to be ready before starting the portal
echo "  Waiting for CVCE health check..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8400/health > /dev/null 2>&1; then
    echo "  ✓ CVCE ready"
    break
  fi
  sleep 1
done

# ── Portal ─────────────────────────────────────────────────────────────────────
echo "▶ Starting Portal on :3000..."
cd "$PORTAL_DIR"
npm run dev &
PORTAL_PID=$!

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  CVCE   → http://localhost:8400"
echo "  Portal → http://localhost:3000"
echo "  Ctrl-C to stop both"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
wait
