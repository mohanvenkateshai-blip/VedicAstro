#!/usr/bin/env bash
# Convenience runner for corpus embeddings generation.
#
# Responsibilities:
# - Source portal/.env.local so GEMINI_API_KEY (and Supabase keys) are exported.
# - Forward args (e.g. --limit N, --dry-run) to the generator.
# - Log everything (unbuffered) to embeddings-run.log at repo root.
# - Call a desktop notify at end (terminal-notifier if present, else osascript on macOS).
# - Print exact follow-up verification commands.
#
# Idempotent-friendly: generator only touches rows with embedding IS NULL,
# so re-running this script (or the python directly) is safe and resumes.
#
# Usage:
#   ./scripts/run-embeddings.sh --limit 50     # safe first batch
#   ./scripts/run-embeddings.sh                # full run (all remaining nulls)
#   ./scripts/run-embeddings.sh --dry-run --limit 5
#
# Background (recommended for long runs):
#   nohup ./scripts/run-embeddings.sh > /dev/null 2>&1 &
#   tail -f embeddings-run.log
#
# After schema + sync_chunks, the FIRST real action should be a small test batch.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/embeddings-run.log"
GEN="$ROOT/scripts/generate-embeddings.py"

# Source full portal env (GEMINI_API_KEY, SUPABASE_*, etc.). set -a exports all.
if [[ -f "$ROOT/portal/.env.local" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/portal/.env.local"
  set +a
else
  echo "warn: portal/.env.local not found; relying on current environment" >&2
fi

# Require the key for real work (generator will also check, but fail fast here for clarity).
if [[ -z "${GEMINI_API_KEY:-}" && -z "${GOOGLE_API_KEY:-}" ]]; then
  echo "error: GEMINI_API_KEY or GOOGLE_API_KEY not set (check portal/.env.local)" >&2
  exit 2
fi

# Timestamp header for this invocation (supports multiple runs in same log).
{
  echo "=== embeddings run start: $(date -Iseconds) ==="
  echo "args: $*"
  echo "GEMINI_API_KEY present: $( [[ -n "${GEMINI_API_KEY:-}" || -n "${GOOGLE_API_KEY:-}" ]] && echo yes || echo no )"
} | tee -a "$LOG"

# Run generator, unbuffered, streaming to both console and log.
# Forward all CLI args (e.g. --limit 100 --dry-run).
set +e
python3 -u "$GEN" "$@" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}
set -e

{
  echo "=== embeddings run end:   $(date -Iseconds) ==="
  echo "exit_code: $rc"
  echo
} | tee -a "$LOG"

# Desktop notification (best-effort, never fail the run).
if command -v terminal-notifier >/dev/null 2>&1; then
  terminal-notifier -title "VedicAstro Embeddings" \
    -message "Run complete (rc=$rc). Log: embeddings-run.log" || true
else
  osascript -e "display notification \"Embeddings run done (rc=$rc). See embeddings-run.log\" with title \"VedicAstro\"" 2>/dev/null || true
fi

# Exact follow-up verification commands (copy/paste ready).
cat <<'EOF' | tee -a "$LOG"

Follow-up verification commands (run these next):

# 1) Quick local dry-run to confirm no (or few) nulls remain:
python3 scripts/generate-embeddings.py --dry-run --limit 5

# 2) Local KnowledgeEngine probe (vector flag + sample search). Requires env:
source portal/.env.local
python3 -c '
import os, sys
sys.path.insert(0, "cvce")
from knowledge_engine.engine import KnowledgeEngine
ke = KnowledgeEngine()
print("vector_search_available:", ke.vector_search_available())
hits = ke.search("dasha", top_k=3)
print("search_hits:", len(hits))
for h in hits[:2]:
    print("  -", h.get("source_id"), "sim=", round(h.get("similarity", 0), 4) if h.get("similarity") else None)
'

# 3) If you have a running local CVCE:
# curl -sS "http://localhost:8000/knowledge/health" | python3 -m json.tool || true
# curl -sS "http://localhost:8000/knowledge/search?q=muhurta&top_k=3" | python3 -m json.tool || true

# 4) Production Learn smoke (after any portal deploy that depends on this):
# ./scripts/smoke-learn-production.sh

# 5) To watch a background run:
# tail -f embeddings-run.log

EOF

exit "$rc"
