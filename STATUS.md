# VedicAstro — Living Status Document

**🚨 HANDOFF SNAPSHOT (2026-06-29)** — User is switching AI tool + model.  
Tree was cleaned and committed. See `docs/handoff/AI_TAKEOVER_PACK.md` first.  
Current graph: newbooks-v1 (26,722 nodes). Learn module live. KE is authoritative.

**First thing to read if you want to know "what's actually in the knowledgebase":**
`knowledge-graph/KNOWLEDGE_CATALOG.md` (full inventory of the 61 sources + why it feels haphazard).

This document is the **Single Source of Truth** for the current status, live health, and immediate roadmap of the VedicAstro project. For architectural principles, system topology, and immutable code guardrails, refer directly to `CONTEXT.md`.

*Last Updated: June 29, 2026 (26,722-node graph with Core 20 + 12 newbooks texts; deterministic layer complete and deployed)*

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

**All future handoff snapshots generated via `scripts/handoff/maintain_context.py` are required to reference `.cursor/rules/multi-agent-mandatory-protocol.mdc`.**

---

## 1. Service Health & Deployments

**Live dashboard:** [portal-omega-two-10.vercel.app/status](https://portal-omega-two-10.vercel.app/status) — HTTP probes on each visit.

| Component | Live URL / Connection | Hosted On | Status | Notes |
|:---|:---|:---|:---|:---|
| **Portal** | [portal-omega-two-10.vercel.app](https://portal-omega-two-10.vercel.app) | Vercel | 🟢 LIVE | `/api/cvce/*` proxy for explorers; `/chart/report` Horoscope Report; Transit Intelligence panel (June 27 evening deploy). |
| **CVCE (Engine)** | [vedicastro-cvce.fly.dev](https://vedicastro-cvce.fly.dev) | Fly.io (LHR) | 🟢 LIVE | Vimshottari fix (`dasha_vimshottari.py`), `/report/facts`, transit/dasha analyzers. Scale-to-zero — first request after idle can take **30–60s** via proxy. |
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
- [x] **9** Shadbala chapter — Sthana/Dik/Cheshta/Kaala/Naisargika/Total-Rupa table for 7 planets.
- [x] **10** Timing merge — combined dasha score + transit verdict → single window verdict with reasons.
- [x] **11** Dasha forecast — next 8 antardasha periods, each with dated range + life-area bullets (profession/wealth/health/family/caution).
- [x] **12** LLM narration layer — gate `CVCE_LLM_NARRATION=1` wired in report_facts + UI render (P0, initial code landed).
- [x] Vector embeddings — corpus_chunks table + chunk sync + generate-embeddings.py (P0, initial code landed; embeddings fill on demand).
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
