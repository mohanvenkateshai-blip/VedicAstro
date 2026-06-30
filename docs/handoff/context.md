# VedicAstro — Session Handoff Context

**Snapshot:** 2026-06-30 (post Learn full-chapters rollout + auth fix)  
**Purpose:** Preserve working context across Cursor/software updates. Read this first, then `CONTEXT.md` (guardrails) and `docs/handoff/AI_TAKEOVER_PACK.md`.

---

## 1. What We Were Doing (This Session)

User goal: **Present every book in `/learn` as clean chapters from local Graphify sources** (structured JSON + raw markdown), without depending on Supabase for text bodies or burning paid API credits.

**Outcome:** Rolled out via 7 parallel agents. **60/61 books** have authoritative structured chapters; **1 edge case** degrades gracefully. Local dev verified; **production deploy is stale** (smoke 3/7 until push).

Secondary fix: **NextAuth `MissingSecret` console error** — auth now skips initialization when env vars are placeholders; Learn works in anonymous mode.

---

## 2. Current Live State (Counts Only)

| Asset | Count / Status |
|-------|----------------|
| Graph version | `newbooks-v1` — ~26,722 nodes |
| Manifest sources | 61 |
| Structured JSONs | 61 (+ AUDIT_SUMMARY) |
| Books with structured chapters | **60** |
| Zero-chapter structured book | **1** — `Jataka_Tatva_Mahadeva` |
| Local raw markdown | 61 files in `knowledge-graph/raw/` (not committed; IP policy) |
| Node-chapter patches | ~16k global + 16+ per-book `patch-*.json` |
| Embeddings | **Blocked** — Gemini quota exhausted; do not run `generate-embeddings.py` until credits restored |
| Supabase `corpus_chunks` | Schema applied by user; partial sync existed; not required for Learn reader |

---

## 3. Learn Module — How It Works Now

**Pipeline (uniform for all books):**

1. `portal/src/lib/books.ts` — resolve structured book (fuzzy on bookId/stem/canonical)
2. `chaptersFromStructured` → authoritative left-nav TOC
3. `loadLocalRawMarkdown` / `loadFullMarkdownForBook` — **local first** (`knowledge-graph/raw/` or bundled `portal/data/raw/`)
4. `sectionsFromStructured` — slice real prose via `start_line` / `end_line`
5. Fallback: `parseMarkdownToSections` (improved junk filter) when no structured chapters
6. Patch enrichment via `loadNodeChapterPatch` (per-book patch + global map)

**Key files changed this session:**

- `portal/src/lib/books.ts` — fuzzy raw discovery, `getFullBookMarkdown`, improved parse fallback
- `portal/src/app/(main)/learn/[bookId]/page.tsx` — `loadFullMarkdownForBook`, local-first content
- `portal/src/components/BookReaderClient.tsx` — structured vs section labeling
- `portal/src/app/(main)/learn/page.tsx` — chapter counts for fallback books
- `portal/scripts/sync-structured-data.mjs` — copies structured + patches + **raw** → `portal/data/`
- `portal/src/lib/auth-config.ts` + `portal/src/app/api/auth/auth.ts` — conditional NextAuth (no MissingSecret)

**Data sync command:**

```bash
cd portal && npm run data:sync   # or npm run dev (predev runs sync)
```

---

## 4. Verification (Run After Any Learn Change)

```bash
# Local
cd portal && npm run typecheck
node scripts/verify-structured-path.mjs
python3 ../scripts/verify_structured_books.py

# Local dev server (user browser — agent shell may not share localhost)
cd portal && npm run dev
# Spot-check: /learn/Jaimini_Sutras, /learn/Ashtakavarga_System_Comprehensive_Handbook

# Production gate (MANDATORY before marking Learn work DONE)
./scripts/smoke-learn-production.sh
# Expect after push: jaimini redirect, structured signals on Jaimini + Hora, chapter labels on /learn
```

**Last known smoke (pre-push):** 3 passed / 4 failed — stale Vercel deploy.

**Representative book verify:** 6/7 PASS (`LEARN_FULL_CHAPTERS_STATUS.md`).

---

## 5. Git / Deploy Status

- **Branch:** `main`
- **Working tree:** **Dirty** — many uncommitted changes from Learn rollout, KG patches, structured JSON updates, auth fix, docs
- **Recent commits on origin:** Learn structured library fixes, token discipline, Hora TOC fix, Jaimini ilike
- **Not pushed:** Current session's Learn-all-books + auth changes likely still local

**Before user-visible prod fix:** commit relevant portal files → push → wait for Vercel → re-run smoke.

---

## 6. Explicit Do-Not-Do (Hard-Won)

1. **Do not run Gemini embeddings** until user confirms credits — burned quota this session.
2. **Do not ask user to run commands you can run** — start dev server, verify, sync data yourself.
3. **Do not mark Learn work DONE** without `./scripts/smoke-learn-production.sh` passing on prod.
4. **Do not paste full graph.json / node-chapter-map / structured corpora** into chat — use scripts, report counts.
5. **Keep + harden** — do not restart from scratch; local Graphify + structured library is the foundation.
6. **Muhūrta standalone is FROZEN** — iframe only at `/muhurta`.

---

## 7. Pending / Next Natural Work

| Priority | Task | Notes |
|----------|------|-------|
| P0 | **Push + prod smoke** | Unblocks user-visible Learn rollout |
| P1 | Rebuild structured chapters for `Jataka_Tatva_Mahadeva` | Only zero-chapter book |
| P2 | Embeddings (when credits return) | `scripts/generate-embeddings.py`; schema ready |
| P2 | Supabase provenance patches | `apply_node_chapter_patch.py --supabase --write` (UPSERT fixed) |
| P3 | Patch chapter_id overlap on some classics | Jaimini ~2%, BPHS ~16% — affects provenance labels, not TOC |

---

## 8. Agent Protocol (Project Law)

- **Token discipline:** `.cursor/rules/token-discipline.mdc` — script-first, no corpus dumps, push before DONE.
- **Multi-agent:** `.cursor/rules/multi-agent-mandatory-protocol.mdc` — tiered (0–1 for trivial, 3–5 for library waves, not blind 5+ for single bugs).
- **Handoff maintainer:** `python scripts/handoff/maintain_context.py --update-all` after KG ingest.

---

## 9. Read Order for Next AI

1. **This file** (`docs/handoff/context.md`) — session state
2. `CONTEXT.md` — immutable guardrails + topology
3. `docs/handoff/AI_TAKEOVER_PACK.md` — engine/registry snapshot
4. `docs/knowledge-engine-status.md` — KE capabilities
5. `LEARN_ROLLOUT.md` + `LEARN_FULL_CHAPTERS_STATUS.md` — Learn verification
6. `ROLLOUT_NOTE.md` — multi-agent wave notes (2026-06-30)
7. `knowledge-graph/KNOWLEDGE_CATALOG.md` — what's actually in the library

---

## 10. User Context (Non-Technical)

- User switched xAI/Cursor accounts mid-session — unrelated to codebase; Cursor account vs xAI API key are separate.
- User frustrated by slow progress + API credit burn earlier — **zero-cost local work preferred**.
- User wants autonomous execution — run dev server, verify, push; don't delegate manual steps.
- Local dev was working after auth fix (HMR connected, no MissingSecret).

---

*Regenerate broader handoff artifacts after KG changes:*
```bash
python scripts/handoff/maintain_context.py --update-all
```
