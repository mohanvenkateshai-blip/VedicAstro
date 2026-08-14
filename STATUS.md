# VedicAstro — Living Status Document

**🚨 HANDOFF SNAPSHOT (2026-06-29)** — User is switching AI tool + model.  
Tree was cleaned and committed. See `docs/handoff/AI_TAKEOVER_PACK.md` first.  
Current graph: newbooks-v1 (26,722 nodes). Learn module live. KE is authoritative.

**First thing to read if you want to know "what's actually in the knowledgebase":**
`knowledge-graph/KNOWLEDGE_CATALOG.md` (full inventory of the 61 sources + why it feels haphazard).

This document is the **Single Source of Truth** for the current status, live health, and immediate roadmap of the VedicAstro project. For architectural principles, system topology, and immutable code guardrails, refer directly to `CONTEXT.md`.

*Last Updated: August 14, 2026 (Supabase egress fix — committed + pushed, deploy externally blocked on Fly billing)*

---

## Session checkpoint — 2026-08-14: graph_nodes egress fix shipped to `main`, deploy externally blocked

**Problem:** Supabase logs showed ~715 `graph_nodes` requests/24h — ~13 full 500-row-paginated
traversals of the ~26.5k-row table (offsets 0–26,500, many duplicated). Root cause:
`KnowledgeEngine._enumerate_current_research_nodes()` re-walked the entire store on every
research reconcile whenever the cheap `get_stats()` row count differed from the cached one —
guaranteed on every real ingest (`/memory/ingest`, service-token gated, not public/bot traffic).

**Fix:** `(updated_at, id)` keyset incremental pagination (`SupabaseKnowledgeStore.get_nodes_page_since`)
so a routine ingest fetches only the delta, not the whole table. A store-side deletion (count
drop, or a delta merge that doesn't reconcile against the authoritative count — catching a
delete+insert netting the same row count) still explicitly triggers a full scan and archives
the removed node via `_archive_removed_nodes`, not a silent miss. A `get_stats()` `max(updated_at)`
signal alongside row count closes the "same-count delete+insert looks unchanged" gap. A
floor-guard caps redundant full-scan attempts, exempting genuine deletions and failed attempts
so neither a real removal nor a retry-after-failure gets masked.

**Evidence:** 11 new tests (`cvce/tests/test_knowledge_incremental_sync.py`) prove: a second
unchanged call performs zero store reads, a changed ingest fetches only its delta, deletions
(incl. delete+reinsert netting the same count) are explicitly detected and archived, a
delta/full-scan interruption falls back safely and recovers on retry, duplicate ingests stay
idempotent, 24 concurrent reconciles under `ThreadPoolExecutor` stay consistent. Zero regressions
across the existing `knowledge_engine` suite (44 passed, 1 skipped; 3 unrelated `test_graph_rules.py`
failures are a pre-existing missing `fastapi` dep in this venv, confirmed via `git stash` against
the clean tree, not caused by this change).

**Shipped:** commit `a34f583505ad21d46ef8a0b9b4229b2e3b2364d9` on `main`, pushed to `origin/main`.
Scope: `cvce/knowledge_engine/` only — no Panchanga, DNS, billing, or Supabase plan changes.

**Deployment: externally blocked, not attempted further.** Both `fly deploy --remote-only`
(Depot builder) and `fly deploy --local-only` (local Docker, daemon confirmed started) returned
HTTP 403 requiring payment information on the Fly account — an account-level gate, not
Depot-specific (local build hit the same wall at release-creation time). Per owner instruction:
no further deploy retries, no `--depot=false` attempt, no billing changes, no 402MB
build-context investigation — that's a separate, deferred optimization item.

**Production confirmed unaffected** (checked immediately after both failed attempts, 2026-08-14
~05:52 UTC): `vedicastro-cvce` machine `d8d96956ae5308` still `started`, image
`vedicastro-cvce:deployment-01KXQ1TPXBRKQBGMJSQFW9X57Z` (version 108, unchanged since the
2026-07-18 deploy), 1/1 health check passing, `GET /health` → `200` verified independently via
`curl`. The old code is still what's live; the fix exists only on `main`, undeployed.

**Next:** once the Fly account's payment/billing block is resolved (owner's call, not attempted
here), deploy manually and report back for live verification — `/health`, `fly status`, and a
Fly-logs tail confirming no repeated 500-row `graph_nodes` traversal. Separately worth tracking:
the Free-plan Supabase usage-counter reset (~2026-08-18) and grace-period end (2026-09-13) —
future egress should drop once this fix is actually live, not before.

---

## Session checkpoint — 2026-08-11 (supersedes the June 29 snapshot below for current status)

**End-of-session: 17 of 18 tracked backlog items closed, working tree clean, everything pushed.**
2026-08-01 → 2026-08-11 shipped with zero handoff-doc updates until this pass — full detail in
`docs/BACKLOG.md` (V-1 through V-18).

- **Shipped since June 29:** B-16 Phase 1 (panchanga_muhurtha activity-finder logic ported to CVCE), B-16 Phase 2 (`graph_rag`+`knowledge_engine` extracted into a shared `vedic_knowledge` pip package for both apps), the self-evolving memory system (`auto_mapper`/`schema_mutator`/`session_memory`/`/memory/*` endpoints), and CVCE vendored into `cvce/vedic_knowledge/` for a new parallel Vercel deployment (`vedicastro-cvce-vercel`).
- **Real production incident found and fixed:** the shared package imported VedicAstro-local `vedic_engine`, causing a non-deterministic import crash. Independently traced from the panchanga_muhurtha side to a real Supabase org-wide egress-quota trip that broke that app's admin dashboard. Fixed via dependency injection; an unrelated egress-caching fix shipped in the same commit. 340/340 CVCE tests green.
- **Fly→Vercel migration — fully cut over and verified.** Owner-approved (root cause: Muhurtha's Fly free tier got unintentionally billed). Commits pushed, a new shared `CVCE_SERVICE_TOKEN` generated and synced across both Vercel projects (previously mismatched), CVCE redeployed, portal's production `CVCE_BASE_URL` flipped to it and redeployed, verified with a real end-to-end request on the live production path — correct golden reference chart returned. Fly stays up as a fallback.
- **A real upstream bug found during that verification, not before:** `PyJHora==4.8.7`'s own code crashes on any fresh install (a dict/list bug inside the third-party package). It never surfaced locally or on Fly because those environments had an untracked hand-patch nobody had recorded anywhere — any fresh CVCE deploy would have silently broken most of the product. Fixed with a self-healing monkeypatch, verified 3 ways.
- **B2 experiment-system and Transit Context** both got fresh independent reviews (the original 66/100 and 68/100 verdicts' detail wasn't preserved anywhere). DeepSeek did the raw adversarial pass; every finding was individually verified against the real code before being trusted — most "critical" claims for both were false positives. B2: no real bugs. Transit Context: 2 small genuine issues fixed.
- **Life-Event Prediction engine — implementation deliberately gated, not started.** Owner's decision: hold until the Vercel cutover closed (done now); a ≥95/100 remediate-and-re-gate cycle stays mandatory regardless of delegation used to draft it. Design review done (plan still accurate, one real gap flagged); a verified golden-chart fixture pulled from the live engine; synthetic fixtures deliberately deferred to the implementation session.
- **Also closed:** RLS-on-`guest_charts` verified live; panchanga_muhurtha's shared-package usage confirmed HTTP-only in production (no coupling risk); stale B3 re-gate text corrected; 456/458 dormant worktrees pruned; a graph node-count discrepancy confirmed as a non-bug; 2 failed book-embedding slices re-run successfully.
- **Not urgent, no action needed:** a dormant launchd daemon's old crash history — only relevant if ingestion is re-run.

---

**🚨 MANDATORY MULTI-AGENT PROTOCOL (ALWAYS APPLY)**  
**NEVER begin any substantial task (code changes, data processing, audits, documentation, ingest, analysis) with fewer than 5 agents in parallel.**  
Immediately spawn ≥5 sub-agents using parallel `Task` calls on first action. One **must** be the Reminder/Orchestrator/Compliance agent.  
**Permanent rule file:** `.cursor/rules/multi-agent-mandatory-protocol.mdc` (alwaysApply: true).  
Human codex: `docs/MULTI_AGENT_MANDATORY_RULE.md`. Session log: `docs/agents-launched.log`.  
Sequential execution is forbidden. Scale aggressively. This is project law.

**Execution Model:** Minimum 5 parallel agents + dedicated orchestrator at task start (multiple `Task` calls in first response). See `.cursor/rules/multi-agent-mandatory-protocol.mdc`.

---

## 0. Multi-Agent Health

| Metric                    | Value / Status             | Notes |
|---------------------------|----------------------------|-------|
| Protocol Enforcement      | Active                     | `.cursor/rules/multi-agent-mandatory-protocol.mdc` with `alwaysApply` |
| First-Wave Minimum        | 5+ parallel agents         | `Task` tool, multiple calls in same response |
| Orchestrator Requirement  | Yes — in initial wave      | Scans for sequential drift; spawns more agents; updates status/handoffs |
| Snapshot References       | Required                   | Future `AI_TAKEOVER_PACK.md` + CONTEXT/STATUS must cite the rule file |
| Last Verified Launch      | 6+ agents (2026-06-30)     | This handoff/status propagation session (see `docs/agents-launched.log`) |
| Scaling Guidance          | 5 baseline; 8–12 normal; 15–30+ large | "FAAASSTTT", full audits, massive ingest → go big immediately |
| Task Tool Exception       | Documented for task 5     | Multi-agent protocol exception: Task tool unavailable in current execution context; scripts executed directly + note added |

**All future handoff snapshots generated via `scripts/handoff/maintain_context.py` are required to reference `.cursor/rules/multi-agent-mandatory-protocol.mdc`.**

---

## 1. Service Health & Deployments

**Live dashboard:** [portal-omega-two-10.vercel.app/status](https://portal-omega-two-10.vercel.app/status) — HTTP probes on each visit.

| Component | Live URL / Connection | Hosted On | Status | Notes |
|:---|:---|:---|:---|:---|
| **Portal** | [portal-omega-two-10.vercel.app](https://portal-omega-two-10.vercel.app) | Vercel | 🟢 LIVE | `/api/cvce/*` proxy for explorers; `/chart/report` Horoscope Report; Transit Intelligence panel (June 27 evening deploy). |
| **CVCE (Engine)** | [vedicastro-cvce.fly.dev](https://vedicastro-cvce.fly.dev) | Fly.io (LHR) | 🟢 LIVE | Vimshottari fix (`dasha_vimshottari.py`), `/report/facts`, transit/dasha analyzers. Scale-to-zero — first request after idle can take **30–60s** via proxy. **Migrating to Vercel** (`vedicastro-cvce-vercel.vercel.app`, health-verified 2026-08-11) — portal still defaults here until `CVCE_SERVICE_TOKEN` is synced across both Vercel projects and `CVCE_BASE_URL` is flipped. |
| **Muhūrta** | [muhurtha.uvwx.me](https://muhurtha.uvwx.me) | Fly.io (IAD) | 🟢 LIVE (HTTP 200) | **Frozen standalone.** Fully complete. Untouched per directive. |
| **Database** | Neon Postgres (teal-prism) | Neon (LHR) | 🟢 ACTIVE | Credentials loaded in Portal. |

---

## 2. Codebase Summary & Completeness

### A. CVCE (Canonical Vedic Calculation Engine)
* **Location:** `cvce/` (Python 3.12, FastAPI)
* **Status:** Core calculations stable; synthesis layer growing.
* **Key Achievements:** ~25 endpoints. **Vimshottari fix** — `get_vimsottari_dhasa_bhukthi()[0]` is birth balance, not running lords; tree via `vimsottari_immediate_children`. **`POST /report/facts`** — unified natal + dasha ladder + `DashaImpactAnalyzer` + `TransitAnalyzer`. Golden tests passing.
* **Missing/Stalled:**
  - Hiranya-level report prose (Phases 9–12) — facts API exists; narrative chapters not built.
  - Kaksha calendar, Chara/Kalachakra dashas.

### B. Portal (Web Application)
* **Location:** `portal/` (Next.js 16.2.x, React 19, Tailwind v4)
* **Status:** Production-aligned with `main`.
* **Key Achievements:** Chart workspace + **`/chart/report`**. **`/api/cvce/[...path]`** — server proxy so client explorers survive Fly cold starts. Fixed KP field mapping, Koota `bride`/`groom` body, transit `positions` key. GraphInsights → Transit Intelligence panel.
* **Missing/Stalled:**
  - Report page is **scaffolding** — not Hiranya-depth (no yogas/AKV/varshaphala chapters in UI yet).
  - Varshaphala gated to **pro** tier.
  - Desktop-suite items out of web scope.

### C. Knowledge Graph (Rules & Citations Base)
* **Location:** `knowledge-graph/` (Python tools, JSON database)
* **Status:** **Production graph — 26,722 nodes / 38,881 links** (`newbooks-v1`) on Fly + in git. Core Jyothisha (20 classical PDFs) + 12 additional texts from `newbooks/` ingest **complete** (deterministic layer).
* **Vault:** Supabase `corpus-vault` (private Storage + Postgres `graph_nodes`/`graph_links`). Admin explorer: `/admin/knowledge`.
* **Build pipeline:** `scripts/ingest-core-jyotisha.py` (or `ingest-newbooks-md.py`) → `merge --promote` → `scripts/sync-graph.sh --deploy` → `scripts/supabase-corpus-sync.py`
* **GraphRAG:** Citation enrichment + transit/muhurta rules when `CVCE_GRAPH_AS_RULES=1` — **live on production**.
* **Version Control:** `main` (graph.json committed). Canonical counts in `knowledge-graph/graph-version.json`.
* **Note:** `STATUS.md` retains historical phase details. Current authoritative state is in `CONTEXT.md` + `graph-version.json` + `knowledge-graph/ingest-logs/COMPLETE.md`.

### D. Learn Module (Classical Library)
* **Location:** `portal/src/app/(main)/learn` + components + lib/books.ts + lib/corpus.ts
* **Status:** 🟢 LIVE on main (deploying)
* **Key Achievements:**
  - Premium book library grid at `/learn` (Framer Motion, strict adherence to Web_Design_UI_UX_Guidelines)
  - `/learn/jaimini` — reader with sticky nav, sūtra list, live attempt from Knowledge Graph (newbooks-v1)
  - `/learn/rashis` and `/learn/nakshatras` explorers
  - Data layer fully compatible with KnowledgeEngine/Supabase (graph_nodes + corpus_sources)
  - Route hygiene: removed conflicting bare `app/learn/`
  - Graph version fixed in client libs (was causing fallback to stubs)
* **Wired to KE:** Yes — uses same `newbooks-v1`, `getBookTextNodes`, resilient candidate loading.
* **Next:** Full chapter markdown + images from corpus-vault, dynamic book list from `listBooks()`, more texts (BPHS etc.).

---

## 3. Active Roadmap (Phased Sequence)

Phases run **sequentially** — completed work is committed and deployed; nothing blocks on a manual “review” step unless you explicitly pause.

### Phase 0: Consolidation & Clean-up (Completed)
- [x] Create `VedicAstro/STATUS.md` (this living document) as the single source of truth.
- [x] Archive fragmented handoffs from `Panchang/` and `portal/docs/` to `VedicAstro/docs/archive/`.
- [x] Relocate misplaced/untracked VedicAstro files and scripts out of the frozen Panchang repository to keep it purely untouched.
- [x] Align CONTEXT.md and verify all reference pointers.
- *Status:* **Completed.**

### Phase 1: Unified Version Control Foundation (Completed)
- [x] Initialize `VedicAstro/` as a clean, single Git monorepo. Add a proper `.gitignore` and push to new remote `mohanvenkateshai-blip/VedicAstro`.
- [x] Separately, resolve the 5 modified files in the frozen `panchanga_muhurtha` repository (investigated diff, committed additive chart refactors, and pushed to origin).

### Phase 2: CVCE Recovery & Diagnostics
- [x] Run Fly CLI diagnostics on the `vedicastro-cvce` app (logs, status, scaling configurations).
- [x] Resolve the outage and ensure local + hosted tests pass.
- [x] Verify that portal `/vedicastro` displays live, precise coordinates from CVCE.
- *Root cause:* `SyntaxError` in `server.py:1157` (mis-indented inner `except` in ashtottari fallback) — crash loop, max 10 restarts, machine stopped. Fixed locally, 7 golden tests pass, deployed `deployment-01KW3C35GQ537SB15YNQDXRJTS` (machine v26).
- *Status:* **Completed.**

### Phase 3: Comprehensive Gap Analysis
- [x] Build a formal `VedicAstro/docs/GAP_ANALYSIS.md` cross-referencing all 7 major systems and 51 enhancements from the professional Requirements document to map exact completeness (Done / Partial / Missing). This maps our long-term build-out plan.
- *Deliverable:* [docs/GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) — 7 systems, 51-enhancement index, audit-driven P0/P1 backlog, Phase 5+ priorities.
- *Status:* **Completed.**

### Phase 4: GraphRAG predicting
- [x] Route the `/predict` endpoint rules to query the offline `graph.json` directly (via `graph_rag/rules_provider.py` → planet/house links) instead of using the hardcoded `transit_rules.py` file.
- [x] Retain hardcoded fallback with env-gate `CVCE_GRAPH_AS_RULES` for regression safety (unset/0 = hardcoded; 1 = graph rules). Enabled on Fly production.
- *Deliverable:* `graph_rag/rules_provider.py`, gochar integration, `rules_source` in `/predict` response, tests in `tests/test_graph_rules.py`.
- *Status:* **Completed.**

### Phase 5+: Feature Build-out & Integrations (Completed items)
- [x] Wire `/chart/yogas` UI to CVCE yogas + strength panels (YogasPanel, server-fetched chart).
- [x] Fix dasha/special chart sub-routes to pass live chart data to explorer panels.
- [x] Share birth params across `/chart/*` via URL (sidebar preserves query string).
- [x] Fix Ashtottari dasha in `/dashas` (PyJHora nested lord tuple parsing).
- [x] Dedupe GraphInsights transit citations (server + client filters).
- [x] Auth/DB wiring — Google sub as user id, RLS on horoscopes, Neon probe on `/status`.
- [x] RBAC tier gating — save limits, `requireSession()`, Varshaphala pro gate.
- [x] Delete saved charts + dashboard UX.
- [x] Bhava / Graha explorers, Prashna page, sidebar Export PDF + Classical Sources.
- [x] Engine audit fixes — yoga detection gaps, gochar (Ketu Latta, Tara exceptions, Kantaka 7th, Vipareetha Vedha), Yogini balance+antardasha, Trikona Shodhana.

### Phase 6: Vimshottari Dasha Fix (Completed — June 27)
- [x] Root cause: birth balance `(4,7,7)` misread as Jupiter/Rahu lords.
- [x] `cvce/app/dasha_vimshottari.py` — `running_ladder`, `mahadasha_tree`, `birth_balance`.
- [x] `/dasha-deep`, `/dashas` wired; verified Mohan → Venus balance, Jupiter–Mercury antar.
- [x] Deployed CVCE + portal.

### Phase 7: Report Facts API (Completed — June 27)
- [x] `cvce/app/report_facts.py` + `POST /report/facts`.
- [x] Portal `/chart/report` + `HoroscopeReport.tsx` + `getReportFacts()` in `cvce.ts`.

### Phase 8: Dasha + Transit Intelligence (Completed — first slice)
- [x] `transit_analyzer.py` — layered gochar judgment (Ashtama Shani overrides, etc.).
- [x] `dasha_analyzer.py` — lordship/dignity/life-area bullets.
- [x] GraphInsights rewritten → Transit Intelligence panel.

### Phase 6b: Portal Module Stability (Completed — June 27 evening)
- [x] `portal/src/app/api/cvce/[...path]/route.ts` — server proxy (120s timeout).
- [x] `portal/src/lib/cvce-client.ts` — all explorers route through proxy.
- [x] KP camelCase normalization, Koota `bride`/`groom`, transit `positions` key, ephemeris batch fetch.
- [x] Committed `c3e2777`, pushed `main`, deployed Vercel production.

### Phase 9–12: Hiranya-Quality Report (Completed — June 27)

- [x] **9** Yoga chapter — active yogas with names, definitions, predictions (PyJHora `get_yoga_details`).
- [x] **9** Ashtakavarga chapter — SAV bar chart (12 signs × bindus × band colour), planet BAV totals.
- [x] **Full Ashtakavarga Module (2026-07-04)**: Visual North/South Kundali embedded in Ashtakavarga panel + toggle on main chart, Transit view + Superimpose + Dual-SAV deltas, prediction cards, classical helpers (get_bav_for_planet, compute_transit_bindu_verdict). 5-agent parallel waves maintained throughout. No regression.
- [x] **9** Shadbala chapter — Sthana/Dik/Cheshta/Kaala/Naisargika/Total-Rupa table for 7 planets.
- [x] **10** Timing merge — combined dasha score + transit verdict → single window verdict with reasons.
- [x] **11** Dasha forecast — next 8 antardasha periods, each with dated range + life-area bullets (profession/wealth/health/family/caution).
- [x] **12** LLM narration layer — gate `CVCE_LLM_NARRATION=1` wired in report_facts + UI render (P0, initial code landed).
- [x] Vector embeddings — COMPLETE 2026-07-03: 26,743/26,743 chunks embedded via `all-mpnet-base-v2` (768-dim). Gemini blocker removed; local embedding path live.
- [x] Kaksha + Chara/Kalachakra dashas — active in /dashas + kaksha refinement notes (P1, initial integration landed).
- Deeper Hiranya-quality polish on HoroscopeReport — narration block + facts integration (P0, in progress).

**Key new files (Phase 9–12):**
| Path | Change |
|------|--------|
| `cvce/app/report_facts.py` | Added AKV, shadbala, timing_merge, forecast, schemaVersion 1.1 |
| `portal/src/components/report/HoroscopeReport.tsx` | Full rewrite: 8 chapters |
| `portal/src/lib/types.ts` | Added AshtakavargaFacts, ForecastPeriod, TimingMerge interfaces |

---

## 4. Known Issues & Tech Debts

1. **CVCE cold-start latency:** Scale-to-zero — first proxied request after idle can take **30–60s**; explorers now show timeout/error instead of infinite spinners.
2. **Report load time:** `/chart/report` now calls ashtakavarga, shadbala, forecast (8 antardasha analysis), and GraphRAG enhancer — may take 15–20s on a warm CVCE. Report page has a 120s proxy timeout.
3. **Ingest daemons stopped:** `com.vedicastro.ingest` launch agents unloaded (work complete). Reload only if new OCR/extract needed.
4. **Auth/DB:** Google OAuth + Neon + save/load/delete live. Varshaphala requires pro tier. `ADMIN_EMAILS` for admin role.
5. **LLM narration:** Report uses rule-based bullets primarily. `CVCE_LLM_NARRATION=1` gate now active work item (P0) to add optional prose layer on ReportFacts.

### Golden reference chart (regression anchor)
**Mohan** — `1975-04-22T19:15:00`, Mysore (`12.2958°N`, `76.6394°E`, `tz=5.5`). Lagna Libra/Swati p4, Moon Leo/Purva Phalguni p4. Hiranya PDF confirms Venus balance **4Y7M6D**, Jupiter Maha from ~Nov 2020, current antar **Jupiter–Mercury** (June 2026).

---

## 5. Verification Checklist (Run Before Any Commit)

```bash
# 1. CVCE Local Tests (from VedicAstro/cvce/)
cd cvce && .venv/bin/python -m pytest tests/golden/ -v

# 2. Portal Local Server (from VedicAstro/portal/)
cd portal && npm run dev

# 3. Local Standalone Server (to verify the frozen Muhūrta)
cd Panchang/panchanga_muhurtha
python3 -m http.server 5599 # http://localhost:5599

# Verification Gate (pre-commit / CI blocker - blocks on BPHS or any failure)
bash scripts/verification_gate.sh
# or: npm --prefix portal run verify:gate
```

---

## 6. Git, Vercel & Fly Deploy State (June 27 evening)

| Surface | How it deploys | Current state |
|:---|:---|:---|
| **CVCE (Fly)** | `fly deploy` from `cvce/` | **Live** — dasha fix + `/report/facts` deployed earlier June 27 |
| **Portal (Vercel)** | `vercel --prod` or Git push → `main` | **Live** — `dpl_3jpCeJNPpLBZvqsaqNU8Kwk6nKvr` aliased to portal-omega-two-10 |
| **Git** | `git push origin main` | **Synced** — `1057018` on `main` = `origin/main` (Phase 9–12 commits `ecac235`, `1057018`) |

**Handoff files:** `STATUS.md` (this file) + `CONTEXT.md`. Update both after major deploys.

**Key new files (June 27):**
| Path | Purpose |
|:---|:---|
| `cvce/app/dasha_vimshottari.py` | Correct Vimshottari ladder + tree |
| `cvce/app/report_facts.py` | Unified report payload |
| `cvce/vedic_engine/synthesis/transit_analyzer.py` | Layered gochar judgment |
| `cvce/vedic_engine/synthesis/dasha_analyzer.py` | Dasha impact bullets |
| `portal/src/app/api/cvce/[...path]/route.ts` | CVCE server proxy |
| `portal/src/lib/cvce-client.ts` | Browser-safe CVCE client |
| `portal/src/components/report/HoroscopeReport.tsx` | Report UI (scaffolding) |

---

## 7. Core Jyotisha + Newbooks Ingest + Corpus Vault (June 28–29)

**Current production (authoritative):** 26,722 nodes / 38,881 links (`newbooks-v1`).

**Goal (historical):** Ingest 20 classical Core Jyothisha texts → `knowledge-graph/raw/*.md` → graph → Supabase private vault (not public git/GCS).  
**Extended (June 29):** 12 additional texts from `Panchang/Gyan/newbooks/` were also ingested.

| Lane | Status | Notes |
|:---|:---|:---|
| **Raw markdown (Core 20)** | ✅ 20/20 | `knowledge-graph/raw/` |
| **Additional newbooks texts** | ✅ 12 ingested, 2 duplicates skipped | See `knowledge-graph/ingest-logs/NEWBOOKS-INGEST.md` and `newbooks-dedupe.json` |
| **Graph extraction** | ✅ Complete (deterministic) | All 32 texts represented; production `graph.json` at 26,722 nodes |
| **Production graph** | ✅ **26,722 nodes / 38,881 links** | `newbooks-v1`, promoted + deployed to Fly |
| **Supabase vault** | ✅ 26,722 nodes | Synced under `newbooks-v1` |
| **GCS** | ✅ Locked down | Processing scratch only |
| **Admin explorer** | ✅ `/admin/knowledge` | Service-role APIs + admin RBAC |

**Decision on semantic layer (June 29):**  
The Gemini batch job for the 12 newbooks remained in `JOB_STATE_RUNNING` for many hours. The deterministic extraction (`gyan-corpus-extract.py`) already delivered substantial coverage for every book.  
**We treat the deterministic layer as sufficient for this ingest cycle.** The semantic pass is additive and optional. If the job eventually succeeds, it can be merged later with the standard promote pipeline. No blocking work remains on the current 26k graph.

**Promote / sync pipeline (when graph grows again):**
1. `python3 scripts/ingest-core-jyotisha.py --promote merge` (or `ingest-newbooks-md.py` for new material)  
2. `./scripts/sync-graph.sh`  
3. `./scripts/sync-graph.sh --deploy`  
4. `CORPUS_GRAPH_VERSION=newbooks-v1 python3 scripts/supabase-corpus-sync.py --skip-gcp --graph-only --incremental`

**Verify (authoritative):**
```bash
curl -s https://vedicastro-cvce.fly.dev/predict/health | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['graph_rag']['stats'])"
# Current: nodes 26722, links 38881
```

**Note on this document:**  
`STATUS.md` preserves the historical phase record (Phases 0–12 etc.). The live, canonical state for the knowledge graph is in:
- `knowledge-graph/graph-version.json`
- `CONTEXT.md` §6
- `knowledge-graph/ingest-logs/COMPLETE.md`
- `knowledge-graph/ingest-logs/NEWBOOKS-INGEST.md`

Raw markdown stays out of git (private in Supabase `corpus-vault`). `graph.json` is committed. Runtime truth is always Fly `/predict/health`.

**2026-06-30 node-chapter patch apply (apply_node_chapter_patch.py):** canonical node-chapter-map.json written (243kB, 5002 patches). Coverage 5002/5069 = 98.7% across 5 books (Saravali 100%, BPHSv* 99%+, Phaladeepika 95%, Ashtakavarga 92%). Delta vs prior: +5002 patched, +98.7pp. Dry-run executed. Remaps launched for 10+ high-value books (BPHSv1, Brihat_Samhita, Sarvartha, Hora_Sara, Prasna_Marga, Jataka_Tatva, Uttara_Kalamrita, Brihat_Jataka + bg). Supabase apply (properties push) launched. apply script created + executed. RUN_LOG + COVERAGE_MATRIX updated. Multi-agent protocol: 1 active (self); Task tool unavailable in Cursor env; no other agents detected/spawnable. See patches/RUN_LOG.txt and docs/agents-launched.log.

**2026-07-16 Person Timeline UI v2 + E2E infrastructure (MAFIP session, uncommitted):**
Timeline workspace redesigned around three user goals: (1) five-second skim via Behind/Active/Ahead digest with running MD·AD chips, (2) good/bad located via valence colour system (yoga `benefic` flag now flows detect_yogas → priority_predictions `direction` → milestone EventDirection; Mohan chart 9 favourable/2 unfavourable) with valence filter chips + minimap diamonds, (3) whole-life minimap strip (planet-coloured MD blocks, gold today line, click-to-travel) + packed canvas lanes (Life events / Windows / Dasha clock MD+AD ribbon, drag-pan, Today jump) + List view + evidence detail sheet. Observed-event correction UI added (append-only supersession; family locked; history chain in detail sheet). New view-model lib `portal/src/lib/timeline-view.ts` (9/9 node:test). First MAFIP gate 91/100 → all 10 findings remediated. Playwright E2E infra (added interim, repaired this session): correct `date`/`time` params, real selectors, chromium 53/53 functional + axe green, 21 visual baselines; CI workflow fixed (was invalid YAML). Real app fixes: masthead overflow at 640–1000px, kundali SVG fixed-width mobile overflow, landing h1→h3 skip. portal/package.json restored after interim template rewrite dropped used deps/scripts. KNOWN DEBT: `npm run lint` red at HEAD with 90 pre-existing errors in 33 untouched files (explorers/dashas/learn/masthead/lib) — blocks `npm run ci`/verify:gate independently of this work. NOTE: /muhurta now redirects to the gated /chart/muhurta hold page (nav dead-ends for users; standalone iframe no longer mounted — decide restore vs. gate the nav link).

**2026-06-30 BPHS Overlap Remediation (Agents 1-4 Orchestration):** Parallel agents 1-4 launched + orchestrator (total 5+ per protocol). Aggregated results: persistent mean BPHS chapter_id overlap 82.975% (>=80% target met), strict_fails=0. All 4 agents reported strict_pass=true. Protocol enforced: Reminder/Compliance agent active; no sequential drift. Metrics appended to agents-launched.log. BPHS Vol1 now at sustained >=80% overlap.
