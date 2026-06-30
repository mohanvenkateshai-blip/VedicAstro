#!/usr/bin/env bash
# Production smoke tests for Portal Learn module.
# Usage: ./scripts/smoke-learn-production.sh [BASE_URL]
# Default BASE_URL: https://portal-omega-two-10.vercel.app

set -uo pipefail

BASE="${1:-https://portal-omega-two-10.vercel.app}"
PASS=0
FAIL=0

ok()  { echo "  PASS: $1"; PASS=$((PASS + 1)); }
bad() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

curl_safe() {
  curl -sS --max-time 25 "$@" 2>/dev/null || return 1
}
curl_head() {
  curl -sS --max-time 25 -I "$@" 2>/dev/null || return 1
}

echo "Learn production smoke — $BASE"
echo

# 1) Jaimini should redirect to structured reader (307/308), not serve old empty page
CODE=$(curl_head -o /dev/null -w "%{http_code}" "$BASE/learn/jaimini" || echo "000")
LOC=$(curl_head "$BASE/learn/jaimini" | grep -i "^location:" | tr -d '\r' || true)
if [[ "$CODE" == "307" || "$CODE" == "308" ]] && echo "$LOC" | grep -qi "Jaimini_Sutras"; then
  ok "jaimini redirect ($CODE → Jaimini_Sutras)"
elif [[ "$CODE" == "307" || "$CODE" == "308" ]]; then
  ok "jaimini redirect ($CODE) — check Location manually: $LOC"
else
  bad "jaimini expected 307/308 redirect, got HTTP $CODE (stale deploy or missing redirect)"
fi

# 2) Jaimini structured page should mention structured chapters, not only frontmatter nav
BODY=$(curl_safe -L "$BASE/learn/Jaimini_Sutras" | head -c 120000 || true)
if echo "$BODY" | grep -qi "structured\|chapter-precise\|Adhyaya\|Contents"; then
  ok "Jaimini_Sutras shows structured reader signals"
else
  bad "Jaimini_Sutras missing structured reader signals"
fi
if echo "$BODY" | grep -qi ">Frontmatter<\|>H1<\|>H2<"; then
  bad "Jaimini_Sutras still shows Frontmatter/H1/H2-only sidebar (node fallback)"
else
  ok "Jaimini_Sutras no Frontmatter/H1/H2-only junk nav"
fi

# 3) Hora should load structured content (not pure node-bucket sidebar)
HORA=$(curl -sL "$BASE/learn/Hora_Shastra_Varahamihira" | head -c 120000)
if echo "$HORA" | grep -qi "structured\|chapter-precise\|Contents"; then
  ok "Hora shows structured reader signals"
else
  bad "Hora missing structured reader signals"
fi

# 4) Jaimini API should return nodes when graph has data (optional — API may be unused after redirect)
API=$(curl -s "$BASE/api/learn/jaimini")
NODES=$(echo "$API" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('nodes',[])))" 2>/dev/null || echo "0")
if [[ "$NODES" -gt 0 ]]; then
  ok "api/learn/jaimini returns $NODES nodes"
else
  echo "  WARN: api/learn/jaimini returned 0 nodes (OK if redirect is primary UX; check ilike fix deployed)"
fi

echo
echo "Result: $PASS passed, $FAIL failed"
if [[ "$FAIL" -gt 0 ]]; then
  echo "Deploy may be stale or structured data not bundled. Push + wait for Vercel, then re-run."
  exit 1
fi
exit 0
