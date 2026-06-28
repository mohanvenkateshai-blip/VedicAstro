#!/usr/bin/env bash
# Apply corpus vault schema to Supabase Postgres.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SQL="$ROOT/portal/supabase-corpus-schema.sql"

if command -v supabase >/dev/null 2>&1; then
  echo "→ supabase db query --linked"
  if (cd "$ROOT" && supabase db query --linked -f "$SQL"); then
    echo "✓ Corpus vault schema applied"
    exit 0
  fi
  echo "warn: supabase CLI failed, trying psql…"
fi

if [[ -f "$ROOT/portal/.env.local" ]]; then
  set -a
  # shellcheck disable=SC1091
  source <(grep -E '^SUPABASE_DB_URL=' "$ROOT/portal/.env.local" | sed 's/^/export /')
  set +a
fi

URL="${SUPABASE_DB_URL:-${1:-}}"

if [[ -z "$URL" ]]; then
  echo "SUPABASE_DB_URL not set."
  echo ""
  echo "Option A — Supabase CLI (recommended):"
  echo "  supabase link --project-ref bfoeygzneobrhtkdjfwc"
  echo "  npm run db:corpus-schema"
  echo ""
  echo "Option B — Supabase SQL Editor:"
  echo "  Paste and run: portal/supabase-corpus-schema.sql"
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "error: psql not found (install PostgreSQL client)"
  exit 1
fi

psql "$URL" -v ON_ERROR_STOP=1 -f "$SQL"
echo "✓ Corpus vault schema applied"
