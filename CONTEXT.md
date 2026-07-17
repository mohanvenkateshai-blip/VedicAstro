# VedicAstro — AI Context Constitution

## Session checkpoint — 2026-07-17 (Timeline v2 shipped; next mission: Life-Event Prediction engine)

- **Shipped & deployed (Vercel + Fly, commits 958f9af..80ffa2a on main):** Person Timeline v2 (digest/minimap/valence canvas/list/correction UI, final MAFIP gate **97/100 PASS**); CVCE valence pipeline (yoga benefic → milestone direction; CVCE suite 340 passed/1 skipped); Playwright E2E suite rebuilt against the real app (chromium 53/53, 21 visual baselines, CI workflow repaired); portal package.json restored after an interim template rewrite dropped used deps; masthead tablet overflow + kundali mobile scaling + landing heading fixes; **/muhurta restored to the frozen standalone iframe per owner decision (80ffa2a)**.
- **Deploy caveat:** Fly has no durable timeline DB volume — `POST /timeline/events` (add/correct observed events) returns 503 in production until `CVCE_TIMELINE_DATABASE_PATH` + volume are provisioned; reads work.
- **Vedic Digest audit (docs/VEDIC_DIGEST_METHOD_AUDIT.md):** handwritten method notes reviewed in full; calculation core aligned; prediction layer deviates — **D1 yoga-first vs event-first (fundamental), D2 no house-network dasha gating, D3 no transit trigger layer, D4 no witness-count confidence, D5 no birth-time stability gate, D6 no varga confirmation.** KG ingest of the digest PDFs: recommended, not yet owner-approved.
- **Owner decisions (2026-07-17):** (a) muhūrta = restore iframe (done); (b) proceed with programme re-gates — Transit Context (last 68/100), B2 (66/100), B3 (re-gate pending); (c) **build the Life-Event Prediction engine** — event-first dated windows (marriage/children/career/foreign/home/health) via six-witness promise + house-network dasha gating + fructification transit narrowing, surfaced on the timeline as checkable claims with hit/miss tally per chart. This is the product's trust engine and the next session's mission; the audit doc is its spec seed.
- **In progress at checkpoint:** portal lint-debt cleanup agent (90 pre-existing errors in 27 untouched files; blocks npm run ci at HEAD); programme re-gate + Life-Event design agents being launched.
- **E2E conventions:** chart pages parse `date`/`time` (never `dob`); local E2E needs CVCE on :8400 and `CVCE_BASE_URL` in portal/.env.local (present); suite docs in memory + STATUS.md 2026-07-16 entry.

## Prediction-engine MAFIP checkpoint — 2026-07-14T15:56:45+01:00

- **Person Timeline gate:** remediation passed independent re-review at **96/100 with zero Critical or High findings**. This supersedes the failed 15:42 checkpoint below; retain the earlier entry as audit history.
- **Integrity and ownership:** stored detail is timeline/subject-bound, portal timeline traffic is bound to an owner-scoped signed guest cookie, forged ownership is rejected, matching criteria are sealed before resolution, and miss/false-alarm verdicts cannot be recorded before the prediction window closes.
- **Verification:** complete CVCE suite **338 passed, 1 skipped** from 339 collected; focused timeline suite **21/21**; portal ownership tests **5/5**; portal typecheck, targeted lint, production build and `git diff --check` passed. Fresh guest access returned HTTP 200, forged ownership returned 403, cross-subject stored detail returned 404, and the live timeline returned 11 milestones, 90 timing periods and zero outcomes.
- **Scientific limit:** prospective prediction ingestion/sealing is not implemented, so the current 11 `engine_inference` bands remain non-prospective research candidates and demonstrated accuracy remains **N/A**. Internal rule scores are not probabilities.
- **Remaining non-blockers:** there is no observed-event correction UI; browser automation remains unavailable, so real-browser pixel, responsive, interaction and accessibility QA is still open.
- **Release state:** Person Timeline passed its local automated/integrity gate, but remains local and uncommitted. No commit, push, Supabase migration, Vercel deployment or Fly deployment was executed.

## Prediction-engine MAFIP checkpoint — 2026-07-14T15:42:44+01:00

- **Person Timeline:** `/chart/timeline` is implemented locally across CVCE and the portal. It separates observed events, migrated non-prospective engine inferences, future prospective predictions, timing periods, activation windows and current outcomes; milestone detail traces the exact MD/AD/PD ladder and links into Dasha.
- **Persistence:** canonical timeline contracts, append-only SQLite storage, resolution history/current-outcome projection and UI/API paths are implemented. Production writes require a durable database path and operating policy; the local default is `/tmp/vedicastro-person-timeline.sqlite3`.
- **Verification:** focused timeline tests passed **18/18**; the integrated CVCE suite passed **335 tests with 1 intentional skip** from 336 collected using the official local Swiss Ephemeris files; `git diff --check`, portal typecheck, targeted lint and production build passed. A live Mohan query returned 11 engine-inference milestones, 90 timing periods, zero outcomes and Swiss Ephemeris 2.10.03 provenance; detail returned the timing ladder; the portal route/proxy included all six lanes.
- **Failed gate:** independent review scored **58/100**, below the required 95. Release blockers are a reproduced cross-subject stored-detail disclosure, missing authenticated owner binding for portal timeline traffic, outcome-aware matching criteria selected during resolution, and the ability to record misses/false alarms before a prediction window ends. The portal must also refresh after saving a resolution. Remediate, add regression tests and run a fresh independent gate before release.
- **Scientific limit:** the 11 current prediction bands are migrated non-prospective `engine_inference` research candidates. There are no clean prospective resolved outcomes, so demonstrated prediction accuracy remains **N/A** and internal rule scores must not be displayed as probabilities.
- **Open acceptance gap:** browser automation could not initialize because its runtime attempted to redefine `process`. Pixel, interaction, responsive and accessibility QA must still be performed in a real browser; an HTTP 200 does not close this gate.
- **Release state:** HOLD. The Person Timeline is suitable only for local remediation/testing at this checkpoint. No commit, push, Supabase migration, Vercel deployment or Fly deployment was executed. Use `docs/prediction-engine-strategy/RELEASE_HANDOFF.md` for bounded staging groups and deployment prerequisites.

## Prediction-engine MAFIP checkpoint — 2026-07-14T14:08:28+01:00

- **Release decision:** HOLD. Transit Context failed independent review at **68/100** and remediation is active; the B2 experiment system entered a third remediation after **66/100**; B3 raw-service remediation is complete but awaits independent re-gate.
- **Native Muhūrta:** `/chart/muhurta` is implemented with a separate IANA-timezone election context, CVCE-only calculation, five-limb Panchanga, verdict/score, factors, avoid windows and provenance. Automated gates are green; pixel-level browser QA remains open because browser control could not initialize.
- **Donor policy:** `docs/prediction-engine-strategy/MUHURTA_REUSE_MANIFEST.md` governs standalone reuse: port validated information patterns, validate rule tables before promotion, and reject wholesale browser-engine/static-DST copying. The existing `/muhurta` iframe remains the migration fallback.
- **Release state:** no commit, push, Supabase migration, Vercel deployment, or Fly deployment was executed. Stage only the bounded groups in `RELEASE_HANDOFF.md`; preserve user-owned exclusions.

## Prediction-engine MAFIP checkpoint — 2026-07-14T12:35:51+01:00

- **Canonical release detail:** `docs/prediction-engine-strategy/RELEASE_HANDOFF.md`.
- **Gate:** Wave A accepted (A1 98/100, A2 96/100, A3 97/100; accepted verification 208 passed, 1 skipped). Wave B is in progress and is not release-gated.
- **Current local verification:** CVCE full suite completed successfully (246 passed, 1 skipped inferred from 247 collected progress markers), compileall and `git diff --check` passed. Exact commands are in the release handoff.
- **Release state:** no commit, push, Supabase migration, Vercel deployment, or Fly deployment was executed at this checkpoint. The mixed dirty worktree includes unrelated user-owned files and must be staged by bounded file group only.
- **Orchestration:** exact per-agent token telemetry and model routing are unavailable; bounded scopes, targeted verification, and checkpoint handoffs are active.

**🚨 HANDOFF SNAPSHOT — 2026-07-03 15:11 IST (Claude Code / Fable 5 session checkpoint)**  
**Latest session handoff: `docs/handoff/context.md` §-1** — Kalachakra full rebuild, Ashtakavarga fixes, app-wide Navagraha color system (all deployed); report-redesign backend (`priority_predictions`) + birth-time rectification engine (`cvce/app/rectification.py`) committed this checkpoint.  
**Product vision (durable):** prioritized/timed/actionable predictions, multi-dasha confluence timing, birth-time rectification as precision prerequisite.  
**Embeddings:** COMPLETE — 26,743 chunks embedded (all-mpnet-base-v2, 768-dim) as of 2026-07-03.  
**Auth:** NextAuth conditional — Learn works without AUTH_SECRET placeholders.  

**Start here, then read in order:**
1. `docs/handoff/context.md` — **latest session handoff (2026-06-30)**
2. `docs/handoff/AI_TAKEOVER_PACK.md`
3. `STATUS.md`
4. `docs/knowledge-engine-status.md`
5. `LEARN_ROLLOUT.md` + `LEARN_FULL_CHAPTERS_STATUS.md`
6. `knowledge-graph/KNOWLEDGE_CATALOG.md`
7. `.cursor/rules/token-discipline.mdc` + `.cursor/rules/multi-agent-mandatory-protocol.mdc`
8. This file (CONTEXT.md) for guardrails.

**🚨 MANDATORY MULTI-AGENT PROTOCOL (ALL TIME — ALL AGENTS — PROJECT LAW)**  
**NEVER start substantial work sequentially or with <5 agents.** At the first sign of any task, immediately call `Task` **multiple times in one response** to launch ≥5 specialized sub-agents in parallel. One of the first wave **MUST** be a Multi-Agent Compliance/Reminder/Orchestrator. Scale to 8–12 (normal) or 15–30+ (large/"FAAASSTTT"). See `.cursor/rules/multi-agent-mandatory-protocol.mdc` (alwaysApply: true), `docs/MULTI_AGENT_MANDATORY_RULE.md`, and `docs/agents-launched.log`.

**Execution Model:** Minimum 5 parallel agents + dedicated orchestrator at task start (multiple `Task` calls in first response). See `.cursor/rules/multi-agent-mandatory-protocol.mdc`. **This rule is permanent and applies in every environment and every session with no exceptions.**

**Read this file before writing any code or making any architectural decision.**
It is the single source of truth for system topology, immutable constraints, and hard-won lessons.

---

## 0. Multi-Agent Health

| Aspect                    | Status                  | Evidence / Notes |
|---------------------------|-------------------------|------------------|
| Protocol Rule             | Active & Enforced       | `.cursor/rules/multi-agent-mandatory-protocol.mdc` (`alwaysApply: true`) |
| Minimum Launch            | 5+ parallel via `Task`  | Required at start of every substantial task (refactors, ingest, audits, docs, fixes, analysis) |
| Reminder/Orchestrator     | Mandatory in wave 1     | Dedicated agent monitors adherence, detects sequential drift, forces more agents |
| Last Session Launch       | 6+ agents               | See `docs/agents-launched.log` (2026-06-30 scaling wave) |
| Handoff Snapshots         | Reference rule          | `AI_TAKEOVER_PACK.md`, maintainer script, CONTEXT/STATUS all declare it |
| Violation Policy          | Direct breach           | "Sequential one-at-a-time" is forbidden except trivial one-line fixes |
| Enforcement               | Permanent & Universal   | Applies in every environment, every session, every agent — no exceptions |

**Future handoff snapshots and the maintainer (`scripts/handoff/maintain_context.py`) are required to surface `.cursor/rules/multi-agent-mandatory-protocol.mdc`.**

---

## 1. System Topology

```
                 ┌─────────────────────────────────┐
                 │       Browser (User)             │
                 └────────────┬────────────────────┘
                              │ HTTPS
                 ┌────────────▼────────────────────┐
                 │    Portal — Next.js 16           │
                 │    Vercel (project: vedicastro)  │
                 │    portal/src/                   │
                 └──────┬──────────────┬────────────┘
                        │ server-only  │ iframe
                        │ lib/cvce.ts  │
              ┌─────────▼──────┐  ┌───▼──────────────────┐
              │  CVCE           │  │  Muhūrta Standalone   │
              │  FastAPI        │  │  muhurtha.uvwx.me     │
              │  Fly.io lhr     │  │  FROZEN FOREVER       │
              │  cvce/app/      │  └───────────────────────┘
              └─────────┬───────┘
                        │ PyJHora
              ┌─────────▼───────┐
              │  Swiss Ephemeris│
              │  (hosted, Lahiri│
              │   sidereal)     │
              └─────────────────┘

              ┌──────────────────────────────────────┐
              │  Knowledge Graph + Corpus Vault       │
              │  knowledge-graph/graphify-out/        │
              │  graph-core-jyotisha.json (merged)    │
              │  → Supabase Postgres + corpus-vault   │
              │  → CVCE /predict when CVCE_GRAPH_AS_RULES=1 │
              └──────────────────────────────────────┘
```

**Three distinct codebases that NEVER share imports, processes, or ports:**

| Component | Location | Runtime | Deploy |
|-----------|----------|---------|--------|
| CVCE (engine) | `cvce/` | Python 3.12 / FastAPI | Fly.io (`vedicastro-cvce`, region `lhr`) |
| Portal | `portal/` | Next.js 16.2.x / React 19 | Vercel (project `vedicastro`) |
| Muhūrta Standalone | `Panchang/panchanga_muhurtha/` | In-browser Babel React | Fly.io separate app + Panchang Vercel |
| Knowledge Graph | `knowledge-graph/` | Offline build + Supabase vault | CVCE Fly deploy via `sync-graph.sh` |

---

## 2. Immutable Guardrails (NEVER violate)

### Architecture
- **The Muhūrta standalone is FROZEN.** `Panchang/panchanga_muhurtha/` is byte-for-byte frozen. Never edit it. The portal's `/muhurta` tab is ONLY an `<iframe src="muhurtha.uvwx.me">` — nothing else.
- **Accuracy = hosted Swiss-Ephemeris only.** No in-browser Keplerian fallback. No approximate calculations. PyJHora + sidereal Lahiri ayanamsa only.
- **Canonical contract = `docs/chart_data.schema.json`.** `cvce/app/chart.py`, `server.py:/chart`, and `portal/src/lib/types.ts` MUST stay in lockstep with this schema. Change the schema → change all three simultaneously.
- **Browser never hits CVCE directly for charts.** `portal/src/lib/cvce.ts` is `server-only` for `/chart`, `/report/facts`, muhurta, etc.
- **Client explorers use the CVCE proxy.** `portal/src/lib/cvce-client.ts` → `POST /api/cvce/{endpoint}` → Fly. Never call `vedicastro-cvce.fly.dev` from client components (cold-start timeouts, CSP).
- **No local cusp calculation in the portal.** Any sidereal astronomy must go through the CVCE API.

### Python (CVCE)
- `cvce/app/ephem.py` is the ONLY file that imports PyJHora. Keep it isolated.
- `requirements-prod.txt` MUST include `geocoder` — PyJHora hard-imports it at module load time even though our endpoints don't use it. Removing it = instant startup crash.
- Config: all settings via env vars prefixed `CVCE_`. No hardcoded URLs, ports, or origins anywhere.
- Redeploy: `cd cvce && fly deploy --remote-only --ha=false`

### Next.js (Portal)
- Framework is **Next.js 16.2.x** — NOT 15, NOT 14. Breaking changes apply:
  - `middleware.ts` is deprecated → use `proxy.ts` with `export function proxy(...)`
  - `searchParams` in server components must be `await`-ed (async)
  - `turbopack: { root: __dirname }` required in `next.config.ts`
- Do not use Next.js 14/15 API conventions. Check official Next.js 16 docs.
- No drop-shadows, no purple, no Geist/system font for headings (see DESIGN.md).

### Design
- **Type:** Fraunces (headings), Sora (body), JetBrains Mono (data). These are locked.
- **Color:** Indigo primary, gold accent (rare). Never purple, never rainbow gradients.
- **Elevation:** color + hairline only. No `box-shadow`.
- Full taste record and drift log: `portal/DESIGN.md`. Append every drift.

---

## 3. Component Constraints

### When working on CVCE (Python)
- Only read/edit files under `VedicAstro/cvce/`
- Run tests: `cd cvce && .venv/bin/python -m pytest` (7 golden tests, must all pass)
- Reference chart: Mohan, 1975-04-22T19:15:00, Mysore (12.2958°N, 76.6394°E, UTC+5.5), Lagna Libra/Swati p4
- Do not import PyJHora outside of `ephem.py`
- Do not conflate Python patterns with Next.js patterns (different deployment, different runtime)

### When working on Portal (Next.js)
- Only read/edit files under `VedicAstro/portal/`
- Do not import anything from `cvce/` or `panchanga_muhurtha/`
- Route structure: `/` = landing, `/vedicastro` = chart page, `/muhurta` = iframe only
- The chart viewer is `components/chart/ChartViewer.tsx` (client component) + `KundaliChart.tsx` (SVG)
- `lib/cvce.ts` is server-only and calls `getChart()`, `getMuhurta()`, `getHealth()`
- `lib/auth.ts` — NextAuth v5 + Neon Postgres; roles `free|pro|premium|admin`; `ADMIN_EMAILS` env for owner admin

### When working on Knowledge Graph
- Source files live in `knowledge-graph/raw/` (**not committed** — vault is Supabase `corpus-vault`)
- Production graph: `knowledge-graph/graphify-out/graph.json` (**committed**, see `graph-version.json` for canonical counts)
- Production deploy copy: `graph.json` → `cvce/data/graph.json` via `./scripts/sync-graph.sh`
- Core Jyothisha ingest: `python3 scripts/ingest-core-jyotisha.py` (convert → extract → merge --promote)
- Supabase sync: `python3 scripts/supabase-corpus-sync.py` (after `gcp-sync-results.sh`)
- Admin explorer: `/admin/knowledge` (service-role APIs, admin RBAC)
- Python interpreter: Panchang venv or `$(cat knowledge-graph/graphify-out/.graphify_python)`
- graph.json structure: keys are `nodes`, `links` (NOT `edges`), `hyperedges`

---

## 4. Cross-System Communication Sequence

```
User fills BirthForm (portal/src/components/BirthForm.tsx)
  → GET /vedicastro?dob=...&lat=...&lon=...&tz=...&place=...
    → portal/src/app/vedicastro/page.tsx (server component, async)
      → await searchParams (Next 16 requirement)
        → lib/cvce.ts getChart(birth) — server-side fetch
          → POST https://vedicastro-cvce.fly.dev/chart
            → cvce/app/server.py _guard("chart", ...)
              → cvce/app/chart.py build_chart_geometry()
                → cvce/app/ephem.py positions(), ascendant(), etc.
                  → PyJHora (Swiss Ephemeris, Lahiri)
              ← returns chart_data (validates against docs/chart_data.schema.json)
          ← chart_data JSON
        ← ChartData TypeScript type (portal/src/lib/types.ts)
      → renders ChartViewer (client) + planet table
```

**Important:** PyJHora takes wall-clock local time + UTC offset on the Place struct. Never pre-convert to UT before passing. This is preserved in `ephem.py`'s `parse_dt()`.

---

## 5. Captured Experience (Known Failure Modes)

These bugs have already been fixed. Don't re-introduce them.

| Bug | Root Cause | Fix Location |
|-----|-----------|--------------|
| `YOGINI_NAKSHATRA_MAP` NameError | `compute_yogini()` referenced undefined dict | `cvce/vedic_engine/prediction/dasha.py:320` — use `_yogini_start()` helper instead |
| Server crash at startup | `geocoder` missing from prod deps | `cvce/requirements-prod.txt` — ALWAYS include `geocoder` |
| Fraunces font axis error | `axes: ["opsz"]` + explicit `weight: [...]` conflict in variable fonts | `portal/src/app/layout.tsx` — use `axes` OR `weight`, never both |
| Place control reset after Compute | Input not round-tripped via URL | `BirthForm.tsx` — `name="place"` persists via GET query string |
| middleware.ts deprecated | Next.js 16 breaking change | Renamed to `proxy.ts`, function named `proxy` |
| Wrong Muhūrta page | Built simplified verdict page instead of iframe | `/muhurta/page.tsx` is ONLY `<iframe src="muhurtha.uvwx.me">` |
| "Horoscope" route | User disliked name | Route is `/vedicastro`, nav label is "VedicAstro" |
| Yogini antardasha equal-division | PyJHora `get_dhasa_bhukthi` at ANTARA level divides maha into 8 equal parts — completely wrong | `cvce/app/dasha_other.py` — bypass PyJHora antardasha; compute proportional from `maha_years × antar_years × year_dur / 36` |
| Vimshottari labels in Yogini section | `AllDashasPanel` rendered `VimshottariCard` before Yogini tree | `portal/src/components/explorers/AllDashasPanel.tsx` — removed VimshottariCard entirely |
| Bharani nakshatra nature wrong | `NAK_NATURE["Bharani"] = "Severe"` — should be Fierce (Ugra class) | `cvce/vedic_engine/core/panchanga.py` — corrected to "Fierce" per Wilhelm Ernst Ch.7 |

### Architecture Pitfalls

- **Context Clash risk:** Python deployment patterns ≠ Next.js deployment patterns. CVCE goes on Fly.io (270MB image, writable FS for ephemeris). Portal goes on Vercel. Do not suggest Vercel for Python.
- **Graph OOM:** Deep BFS on the knowledge graph with no budget cap will exhaust memory. Always pass `--budget N` or `--dfs` for targeted queries.
- **Cusp precision:** Sidereal ascendant calculation uses PyJHora's internal PySwisseph — do not override or approximate it. The golden tests (Mohan's chart: Lagna Libra/Swati p4) validate precision.
- **PyJHora wall-clock convention:** PyJHora expects wall-clock local time + tz offset, NOT UTC. Converting to UTC before passing breaks house calculations.

---

## 6. Knowledge Graph & Corpus Vault (2026-06-29)

**Production graph: AUTO (see KnowledgeEngine stats below)**

New books added (session 2026-06-29): Rath JKRE (+968), Wilhelm Ernst Classical Muhurta (+536),
Vedic Remedies by Rath (+504), Patel/Aiyar Ashtakavarga (+370), Crux of Vedic Astrology (+265),
Jyotish Digest volumes (+273). Total: +3,455 nodes from baseline 23,267.

**Core Jyothisha (20 classical PDFs):**
- OCR/text → `raw/`: **20/20 complete**
- Graph extraction: **20/20 complete** — all books in production `graph.json`

**Corpus vault (Supabase):**
- Tables: `corpus_sources`, `graph_nodes`, `graph_links`, `graph_ingest_runs` (RLS deny-all for clients)
- Storage: private bucket `corpus-vault` (markdown + graph snapshots)
- Sync: `scripts/supabase-corpus-sync.py`; wired as final step of `gcp-sync-results.sh`
- Portal admin: `/admin/knowledge` + `/api/admin/corpus/*` (service role, admin only)

**Production CVCE:**
- `graph.json` on Fly: **26,722 nodes** (deployed 2026-06-29)
- `CVCE_GRAPH_AS_RULES` defaults to `True` — graph feeds transit rules by default
- GCS bucket = processing scratch only (`gcp-lockdown.sh`)

**Git policy:**
- **Commit** `graph.json` + `knowledge-graph/graph-version.json` (canonical node/link counts)
- Do **not** commit `knowledge-graph/raw/*.md` (IP in Supabase Storage)

**Later:** vector embeddings on `corpus_chunks` for hybrid search (not started).

---

## 7. Token Routing

| Task | Model |
|------|-------|
| Deep reasoning, architecture, cross-domain analysis | Opus |
| Coding (Python, TypeScript, components) | Sonnet |
| Rudimentary extraction, simple file ops | Haiku (subagents) |

---

## 8. Engines — Status & Last Knowledge-Graph Feed

<!-- BEGIN AUTO ENGINES -->
| Engine | File (representative) | Purpose | Last KG Feed | Status |
|--------|-----------------------|---------|--------------|--------|
<!-- END AUTO ENGINES --> (AUTO-UPDATED)

<!-- BEGIN AUTO ENGINES -->

| Engine | File | Purpose | Last KG Feed | Status |
|--------|------|---------|-------------|--------|
| Transit rules | `graph_rag/rules_provider.py` | 4-pass GPD+HoraSara+SC consensus for gochar | 2026-06-29 (26,722 nodes) | Live, `CVCE_GRAPH_AS_RULES=True` |
| Muhurta rules | `graph_rag/muhurta_rules_provider.py` | Activity-level muhurta verdicts | 2026-06-29 (26,722 nodes) | Live |
| GraphRAG enhancer | `graph_rag/enhancer.py` | Citation injection on predict responses | 2026-06-29 (26,722 nodes) | Live |
| Natal yoga | `vedic_engine/prediction/yoga.py` | 19 new yogas (Vesi/Vasi, Viparita, Nabhasa…) | 2026-06-29 | Live |
| Muhurta yoga | `vedic_engine/prediction/muhurta_yogas.py` | Full Vara×Tithi+Nakshatra combination tables | 2026-06-29 (Wilhelm Ernst) | Live |
| Dasha (Vimshottari) | `app/dasha.py` | Standard Vimshottari MD/AD/PD | 2026-06-25 | Live |
| Dasha (Yogini) | `app/dasha_other.py` | Yogini with proportional antardasha (classical) | 2026-06-29 | Live |
| Dasha (Ashtottari) | `app/dasha_other.py` | Ashtottari 108-year system | 2026-06-25 | Live |
| Fructification | `app/fructification.py` | Transit×Dasha×Yoga intersection + Vedha | 2026-06-29 (Nakshatra Vedha) | Live |
| Nakshatra Vedha | `app/fructification.py` | Cancels transit results per GPD rule (16th nak) | 2026-06-29 | Live |
| Panchanga | `vedic_engine/core/panchanga.py` | Tithi, Vara, Nakshatra, Yoga, Karana | 2026-06-29 | Live |
| KP System | `app/kp_system.py` | Krishnamurti Paddhati sublord system | 2026-06-25 | Live |
| Varshaphala | `app/varshaphala.py` | Annual return chart | 2026-06-25 | Live |
| Prashna | `app/prashna.py` | Horary chart | 2026-06-25 | Live |

## 9. Next Phases (in priority order) — Active (no longer deferred)

1. **Supabase vault re-sync** — push 26k-node graph when network to Supabase is stable
2. **Vector embeddings on `corpus_chunks`** — hybrid search (P0, schema + sync + generate-embeddings.py landed)
3. **Kaksha calendar + Chara/Kalachakra dashas** — full engine + UI (P1, /dashas integration + Kaksha refinement landed)
4. **LLM narration layer** — optional prose on `ReportFacts` (`CVCE_LLM_NARRATION=1`) (P0, wired + UI render landed)
5. **Deeper Hiranya-quality report UI polish** — complete remaining integration (narration + facts polish in progress)

All items promoted to active work with immediate effect. See STATUS.md §3 and §4 for tracking.

---

## 10. Verify-It-Still-Works Checklist

Before touching any layer, verify the adjacent layer is still healthy:

```bash
# CVCE health
curl https://vedicastro-cvce.fly.dev/health

# CVCE golden tests (run from VedicAstro/cvce/)
.venv/bin/python -m pytest tests/golden/ -v

# Portal (spot check)
# /vedicastro renders Mohan's chart
# /muhurta shows the Muhūrta standalone iframe

# Standalone frozen check (from panchanga_muhurtha/ root)
git status  # should be clean
```
