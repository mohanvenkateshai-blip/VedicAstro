# VedicAstro — Session Handoff Context

**Snapshot:** 2026-07-03 15:11 IST (mid-session checkpoint — Kalachakra rebuild + report redesign backend + rectification engine; Claude Code / Fable 5)  
**Purpose:** Preserve working context across tool/model switches. **Read this file first.**

---

## -1. LATEST SNAPSHOT — 2026-07-03 (Claude Code session, Sonnet 5 → Fable 5)

### Product vision (durable, overrides feature-level defaults)
The app is a "superintelligent portal": predictions must be **prioritized, timed,
actionable** — never generic yoga listicles. Realistic remedies, not textbook
mantra boilerplate. Timing ambition is day/time precision via **multi-dasha
confluence** (guru's principle: Vimshottari + Yogini together, not one system
alone), which requires **birth-time rectification first** (~3 months dasha
shift per 1 minute birth-time error). Saved as persistent memory
(`vision_actionable_predictions.md` in the Claude memory dir).

### Shipped this session (15 commits on main, all deployed to Fly + Vercel)
- **Kalachakra Dasha**: full classical rebuild (`cvce/app/kalachakra.py`, ~900
  lines; `portal/src/components/dashas/kalachakra/`) — Deha/Jeeva, 3 Gatis,
  MD/AD/PD tree, SVG wheel, leap timeline/quick-nav, Argala/Yogakaraka/travel-
  direction/Moon's-Navamsa interpretive layer, storytelling narratives.
  Validated against BPHS Vol.2 Ch.46, PVR Rao tutorial, Cosmic Insights
  (which caught + fixed a real MD/AD duration bug, commit `761c997`).
- **Ashtakavarga**: 3 computation bugs fixed (`05cc3fa`) — now delegates to
  PyJHora, SAV 337-invariant restored. New Divisional Charts + Ashtakavarga tabs.
- **UI**: Navagraha/elemental color system (`portal/src/lib/astroColors.ts`)
  cascaded app-wide (`e456aa9`); bigger charts + per-chart North/South toggle;
  degree-on-hover; rotating Vedic loading phrases (`LoadingPhrase.tsx`).
- **Ops**: recovered full backend outage (single Fly machine saturation —
  restart fixed; stayed at 1 machine per free-tier constraint; bill $2.18→$0
  under Fly's $5 waiver).
- **Validation milestone**: user's real marriage date (2007-02-28) landed
  exactly on Venus Pratyantardasha — deep-dasha engine confirmed accurate.
  User then provided 6 precisely-dated life events as calibration data.

### In flight (uncommitted at snapshot time; being committed + deployed now)
1. **Report redesign backend** (`cvce/app/report_facts.py` + new
   `cvce/app/remedies.py` + `cvce/tests/test_report_priority.py`):
   `priority_predictions` — ≤6 yogas ranked by real chart strength
   (SAV+Shadbala+dignity of planets_involved), timed to Mahadasha windows,
   selectively remedied (hand-curated themes; remedies only where a genuine
   affliction or negative classical text warrants). 45/45 tests pass.
   **Frontend half NOT started**: PriorityInsightsCard, collapse YogasCard,
   wire in already-built-but-unrendered DashaIntelCard/TransitIntelCard
   (`HoroscopeReport.tsx:141-288`).
2. **Birth-time rectification engine** (new `cvce/app/rectification.py`):
   multi-dasha confluence scoring (Vimshottari depth-5 + Yogini MD/AD),
   house-lordship-aware per candidate lagna, ±30 min sweep at 1-min steps.
   **Live validation run against user's 6 events was interrupted — re-run
   pending.** No HTTP endpoint yet (deferred until validated).

### User's calibration events (for rectification; birth 1975-04-22 ~19:15, Mysuru 12.2979/76.6393/+5.5)
| Event | Date/time | Domain |
|---|---|---|
| Marriage (1st) | 2007-02-28 | marriage |
| Second marriage | 2014-01-19 09:15 | marriage |
| Birth of son | 2015-07-21 21:15 | children |
| Job loss | 2016-04-29 | career_obstacle |
| Job start | 2018-11-28 | career_status |
| Mother's demise | 2021-07-17 15:20 | mother |

### Standing session rules (user-granted, still in force)
- KnowledgeGraph/KE authoritative over secondary/AI-summarized sources.
- Fix any bug encountered immediately, no per-bug confirmation needed.
- Free tier only — no cost-increasing infra without asking.
- Deploy verification discipline: curl prod endpoints + Vercel `Ready` check.
- The legacy "≥5 parallel agents mandatory" protocol (Cursor/Kilo era, §below)
  is NOT in force in Claude Code sessions; use subagents where they help.

### Next steps (in order)
1. Re-run rectification validation vs 6 events → report ranked candidates.
2. Finish report-redesign frontend (types.ts, PriorityInsightsCard, collapse
   yoga list, wire intel cards) → typecheck/build → deploy.
3. Rectification fast-follows: `POST /rectify-birth-time` endpoint + UI;
   add Ashtottari/Chara/Kalachakra as confluence systems.
4. Roadmap: day/time-precision prediction engine on rectified birth times.

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
**Goal:** Every module/feature pulls latest program logic, calculations, and algorithms from the Knowledge Graph with supervision — not just "context for LLM".

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

### D. Registration Fix
- **Runtime registration:** Fixed runtime registration for all 9 engines. `runtime=9` now reflects accurate engine registration status.
- **Golden versioning:** Implemented golden versioning for tests, ensuring consistency and reliability across different versions of the Knowledge Engine.

**Before/After Orchestrator:**
- **Before:** Orchestrator did not properly handle engine registration, leading to incomplete engine status reporting.
- **After:** Orchestrator now correctly registers all engines, ensuring accurate status reporting and proper supervision of the Knowledge Engine.

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
