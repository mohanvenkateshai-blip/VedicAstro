# VedicAstro — Living Status Document

This document is the **Single Source of Truth** for the current status, live health, and immediate roadmap of the VedicAstro project. For architectural principles, system topology, and immutable code guardrails, refer directly to `CONTEXT.md`.

*Last Updated: June 27, 2026 (Phases 6–8 committed `c3e2777`; portal + CVCE proxy deployed; `main` synced with origin)*

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
  - `graph-deepseek.json` (10,850 nodes) **not** deployed to Fly — production still on deterministic 4253-node graph.
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
* **Status:** **Production graph — 4253 nodes** on Fly. **DeepSeek extract — 10,850 nodes** in `graph-deepseek.json` (committed, not deployed).
* **Build pipeline:** `scripts/sync-gyan-to-raw.sh` → `gyan-corpus-extract.py` → `graphify-out/graph.json` → `scripts/sync-graph.sh --deploy`. Alternate extractors: `deepseek-graph-extract.py`, `grok-batch-graph-extract.py`, `glm-batch-graph-extract.py`.
* **GraphRAG:** Citation enrichment + transit/muhurta rules when `CVCE_GRAPH_AS_RULES=1` — **done on production**.
* **Removed:** stale `cvce/data/graph.json` (448 nodes) — deleted in `c3e2777`.
* **Version Control:** ✅ `main` at `b002f0d` (June 27 evening).

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

### Phase 9–12: Hiranya-Quality Report (Pending — next priority)
- [ ] **9** Yoga + natal synthesis — planet-in-sign prose, active yogas, shadbala/AKV in report.
- [ ] **10** Timing merge — single judgment combining dasha + transit + vedha + AKV.
- [ ] **11** Life-area forecast — career, wealth, health, marriage with dated windows.
- [ ] **12** Polish — PDF export, classical citations, optional LLM narration layer (facts-grounded only).
- [ ] Deploy `graph-deepseek.json` to Fly after review (do not auto-replace 4253-node graph).
- [ ] Kaksha transit calendar, Chara/Kalachakra dashas, desktop §7 enhancements.

---

## 4. Known Issues & Tech Debts

1. **CVCE cold-start latency:** Scale-to-zero — first proxied request after idle can take **30–60s**; explorers now show timeout/error instead of infinite spinners.
2. **Report quality gap:** `/chart/report` shows engine facts + rule-based bullets — **not** Hiranya-depth narrative. Phases 9–12 pending.
3. **DeepSeek graph not on Fly:** `graph-deepseek.json` committed locally; production CVCE still uses 4253-node deterministic graph.
4. **Documentation drift:** `CONTEXT.md` §8 next-phases list is stale (pre–Phase 6); reconcile when next editing CONTEXT.
5. **Auth/DB:** Google OAuth + Neon + save/load/delete live. Varshaphala requires pro tier.

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
| **Git** | `git push origin main` | **Synced** — `b002f0d` on `main` = `origin/main` (commits `c3e2777`, `7d6eae0`, `b002f0d`) |

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
