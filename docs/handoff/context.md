# VedicAstro — Session Handoff Context

**Snapshot:** 2026-06-30 (end of session — Learn polish + KE Full Update Wave merged to `main`)  
**Purpose:** Preserve working context across Cursor/software updates or when switching to another AI tool. **Read this file first.**

---

## 0. Quick Start for Next AI

```bash
cd /Users/ganesha/Projects/04-UX-Practice/VedicAstro

# KE wave health (9 engines, 10 probes, 0 cracks)
python3 scripts/ke_wave_status.py

# Learn structured library
node portal/scripts/verify-all-learn-books.mjs   # expect 60 structured-pass / 61 manifest

# Portal typecheck
cd portal && npm run typecheck

# Local dev (agent must run this — do not ask user)
cd portal && npm run dev
# → http://localhost:3000/learn

# Production gate for Learn (mandatory before marking Learn DONE)
./scripts/smoke-learn-production.sh
```

**Read order after this file:** `CONTEXT.md` → `docs/KE_FULL_UPDATE_WAVE_2026-06-30.md` → `docs/knowledge-engine-status.md` → `LEARN_FULL_CHAPTERS_STATUS.md`

---

## 1. What Was Accomplished (Full Session Arc)

### A. Learn module — all books with clean chapters (prior milestone, still active)
- **60/61 books** use authoritative structured chapters from `knowledge-graph/structured/*.json` + local raw markdown (`knowledge-graph/raw/` or bundled `portal/data/raw/`).
- **1 edge:** `Jataka_Tatva_Mahadeva` — 0 structured chapters; parse fallback collapses to single "Full Text" chapter for heavy page-scanned OCR.
- Local Graphify is the foundation — **no Supabase download required** for Learn reader bodies.
- NextAuth `MissingSecret` fixed: auth only initializes when real `AUTH_SECRET` + OAuth creds exist; Learn works anonymously.

### B. Learn UI polish (this session, portal)
| Feature | Files | Behavior |
|---------|-------|----------|
| **Global search** | `LearnGlobalSearch.tsx`, `api/learn/search/route.ts`, `learn/page.tsx`, `learn/[bookId]/page.tsx` | Cross-book search on title/chapter/section; debounced dropdown; deep-links with `?chapter=&section=&q=`; "← Back to search results" on book page |
| **Clean tile metadata** | `books.ts` (`humanizeTitle`, `extractDisplayMeta`, `displayTitle`/`author`/`year`) | Tiles show human title + author + year, not raw underscores |
| **Tile overflow fix** | `learn/page.tsx` | `overflow-hidden`, `break-all line-clamp-2` on titles |
| **Scroll-to-top FAB** | `BookReaderClient.tsx` | Fixed bottom-right FAB after scroll (window + reader pane); smooth scroll to top |

### C. KE Full Update Wave (major — merged to `main`)
**Goal:** Every module/feature pulls latest program logic, calculations, and algorithms from the Knowledge Graph with supervision — not just "context for LLM."

**PR (merged locally):** https://github.com/mohanvenkateshai-blip/VedicAstro/pull/3  
**Branch was:** `feat/ke-full-update-wave-2026-06-30` → fast-forward merged into `main` at `c3dc745`.

| Domain | Status | Evidence (counts) |
|--------|--------|-------------------|
| Supervision | DONE | `scripts/ke_wave_status.py`; auditor **10 probes**; **9 engines**, **0 cracks** |
| Panchanga | DONE | 7 panch/tithi books → 28 tithi_lords + 28 effects + 13 yoga attrs + 2 karana; `source_notes` on result |
| Dasha | DONE | 7 dasha books; 8+ Vimshottari variants; period citations e.g. `BPHS:ch-8` |
| Muhurta | PARTIAL (core) | 283 yoga_nodes (was 128); 150+ hits with book citations; portal `/muhurta` still external iframe |
| Transit/Gochar | DONE | 1021 gochara nodes; 9/9 planets enriched; graph citations in compute + analyzer |
| KP/Prashna/Varsha | DONE | 6/6 Jaimini+Prasna books on revive; `ke_version` on special endpoints + proxy |
| Portal surfaces | DONE | `/api/cvce` enriches `ke_version`; Koota, Varshaphala, admin/knowledge show source notes |

**Master tracker:** `docs/KE_FULL_UPDATE_WAVE_2026-06-30.md`  
**Agent reports:** `docs/agent-reports/KE-wave-*.md` (6 files)

**Official KE access (never bypass):** `cvce/knowledge_engine/integration.py`

---

## 2. Current Repository State

| Item | Value |
|------|-------|
| Branch | `main` (KE wave merged; Learn polish committed in same final commit) |
| Graph version | `newbooks-v1` / file-based locally — **26,722 nodes**, **38,881 links** |
| Structured books | 61 manifest; **60 structured-pass**, 1 zero-chapter edge |
| Registered KE engines | 9: ashtakavarga, dasha, gochar, kp_system, muhurta, panchanga, prashna, report, yoga |
| Embeddings | **BLOCKED** — Gemini quota exhausted; do **not** run `generate-embeddings.py` until user confirms credits |
| Raw markdown | 61 files in `knowledge-graph/raw/` (IP — may not all be in git) |
| Patch backups | `knowledge-graph/patches/*.bak-20260630-*` — session backups of node-chapter-map + 4 patch files |

---

## 3. Key Files by Area

### Learn (portal)
- `portal/src/lib/books.ts` — structured resolution, raw loading, display meta, search data
- `portal/src/app/(main)/learn/page.tsx` — library grid + global search
- `portal/src/app/(main)/learn/[bookId]/page.tsx` — book reader server component
- `portal/src/components/BookReaderClient.tsx` — TOC, content, scroll-spy, FAB
- `portal/src/components/LearnGlobalSearch.tsx` — client search UI
- `portal/src/app/api/learn/search/route.ts` — cross-book search API
- `portal/scripts/sync-structured-data.mjs` — copies structured + patches + raw → `portal/data/`

### Auth (conditional — no MissingSecret)
- `portal/src/lib/auth-config.ts` — `isAuthConfigured()`
- `portal/src/app/api/auth/auth.ts` — no-op stubs when auth disabled
- `portal/src/lib/auth/session.ts`

### Knowledge Engine + engines (cvce)
- `cvce/knowledge_engine/integration.py` — **single gateway** (+ `get_registered_engines_with_status()`)
- `cvce/knowledge_engine/refresh_auditor.py` — 10 probes + `run_all_probes()`
- `cvce/vedic_engine/core/panchanga.py` — enriched attrs from structured books
- `cvce/vedic_engine/prediction/{dasha,gochar,muhurta_yogas,kp_system,prashna}.py`
- `cvce/graph_rag/{rules_provider,muhurta_rules_provider}.py` — graph-derived rules
- `cvce/app/server.py` — `/version`, `ke_version` on predict endpoints
- `portal/src/app/api/cvce/[...path]/route.ts` — proxy enriches `ke_version`

### Scripts & verification
- `scripts/ke_wave_status.py` — KE wave dashboard
- `scripts/smoke-learn-production.sh` — prod Learn gate
- `scripts/verify_structured_books.py`
- `tmp_probe_supabase_patches.py` — ad-hoc Supabase patch probe (needs `.env.local` creds)

---

## 4. Learn Pipeline (unchanged core, plus UI)

1. Resolve book via fuzzy `bookId` / stem / canonical (`books.ts`)
2. TOC from `chaptersFromStructured` (structured JSON)
3. Body from `loadLocalRawMarkdown` → slice via `sectionsFromStructured` line ranges
4. Fallback: `parseMarkdownToSections` (junk filter; page-scan collapse for OCR books)
5. Node provenance from per-book patches + `node-chapter-map.json`
6. **New:** Global search indexes all structured books; deep-link scrolls to chapter/section
7. **New:** Tiles show `displayTitle`, `author`, `year`

**Data sync:**
```bash
cd portal && npm run data:sync   # predev/prebuild also runs this
```

---

## 5. Verification Checklist

| Check | Command | Expected |
|-------|---------|----------|
| KE wave | `python3 scripts/ke_wave_status.py` | `engines=9 probed=10 cracks=0` |
| Structured library | `node portal/scripts/verify-all-learn-books.mjs` | `structured-pass=60` |
| Portal types | `cd portal && npm run typecheck` | exit 0 |
| Learn prod smoke | `./scripts/smoke-learn-production.sh` | **Last run: 7 pass / 1 fail** (Hora structured signal — deploy may be stale until push + Vercel rebuild) |
| Local spot-check | `/learn`, search "dasha", open hit, use FAB, check tile titles | titles clean, search works, FAB appears on scroll |

---

## 6. Git / Deploy

- **All session work committed to `main`** in final commit (Learn polish + handoff + remaining artifacts + KE wave already merged via fast-forward).
- **Push to origin** may still be pending — run `git push origin main` to trigger Vercel and refresh prod smoke.
- Open PR #3 can be closed/merged on GitHub if branch was only ahead of old main.

---

## 7. Explicit Do-Not-Do

1. **Do not run Gemini embeddings** until user confirms credits restored.
2. **Do not ask user to run commands you can run** (dev server, verify, push).
3. **Do not mark Learn DONE** without prod smoke passing.
4. **Do not paste full graph.json / node-chapter-map / structured corpora** — use scripts, report counts only.
5. **Do not restart from scratch** — keep + harden local Graphify + structured library + KE integration.
6. **Muhūrta standalone is FROZEN** — `/muhurta` is iframe to `muhurtha.uvwx.me`; internal muhurta logic lives in cvce.
7. **Do not bypass `knowledge_engine.integration`** for graph/rules access in new code.

---

## 8. Pending / Next Work

| Priority | Task |
|----------|------|
| P0 | `git push origin main` + wait for Vercel + re-run `./scripts/smoke-learn-production.sh` until green |
| P0 | Close/merge PR #3 on GitHub if redundant after push |
| P1 | Rebuild structured for `Jataka_Tatva_Mahadeva` (0 chapters in JSON) |
| P1 | Fix Hora prod smoke detection (content good; grep pattern may need tweak) |
| P2 | Embeddings when credits return (`scripts/generate-embeddings.py`) |
| P2 | Supabase provenance sync (`apply_node_chapter_patch.py --supabase --write`) |
| P2 | Deeper KE extraction — conditional rules from books already loaded in dasha/kp/prashna |
| P3 | Runtime registration at cvce startup for all 9 engines (status script shows `runtime: 0` until imports side-effect) |
| P3 | Golden tests versioned by `ke_version` |

---

## 9. Agent Protocol (Project Law)

- **Token discipline:** `.cursor/rules/token-discipline.mdc` — script-first, no corpus dumps, push before DONE on Learn.
- **Multi-agent:** `.cursor/rules/multi-agent-mandatory-protocol.mdc` — tiered (0–1 trivial, 3–5 library/KE waves).
- **Handoff maintainer:** `python3 scripts/handoff/maintain_context.py --update-all` after major KG changes.

---

## 10. User Context

- User wants **autonomous execution** — run dev, verify, commit, push; minimal manual steps.
- User burned Gemini API credits earlier — **zero-cost local work preferred** until credits restored.
- User switched AI/Cursor accounts mid-session — unrelated to codebase.
- User requested **full commit of everything** + this handoff file for continuity in another AI tool.

---

## 11. Session Commits Reference

| Commit | Summary |
|--------|---------|
| `c3dc745` | KE Full Update Wave (30 files: engines, graph rules, auditor, tracker, agent reports, ke_wave_status, portal ke_version surfaces) |
| *(final)* | Learn global search, FAB, display metadata, tile fixes, handoff, verification docs, patch `.bak`s, tmp_probe |

---

*Regenerate broader handoff after KG ingest:*
```bash
python3 scripts/handoff/maintain_context.py --update-all
```
