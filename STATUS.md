# VedicAstro — Living Status Document

This document is the **Single Source of Truth** for the current status, live health, and immediate roadmap of the VedicAstro project. For architectural principles, system topology, and immutable code guardrails, refer directly to `CONTEXT.md`.

*Last Updated: June 27, 2026 (graph corpus 4253 nodes live; graphify deep extract partial; git uncommitted)*

---

## 1. Service Health & Deployments

**Live dashboard:** [portal-omega-two-10.vercel.app/status](https://portal-omega-two-10.vercel.app/status) — HTTP probes on each visit.

| Component | Live URL / Connection | Hosted On | Status | Notes |
|:---|:---|:---|:---|:---|
| **Portal** | [portal-omega-two-10.vercel.app](https://portal-omega-two-10.vercel.app) | Vercel | 🟢 LIVE (HTTP 200) | UI functional; `/vedicastro` server-renders charts via CVCE (verified June 27). |
| **CVCE (Engine)** | [vedicastro-cvce.fly.dev](https://vedicastro-cvce.fly.dev) | Fly.io (LHR) | 🟢 LIVE (HTTP 200) | Restored June 27 — fixed `server.py` ashtottari `except` indentation crash loop; redeployed v26. Scale-to-zero (~3–4s cold start). |
| **Muhūrta** | [muhurtha.uvwx.me](https://muhurtha.uvwx.me) | Fly.io (IAD) | 🟢 LIVE (HTTP 200) | **Frozen standalone.** Fully complete. Untouched per directive. |
| **Database** | Neon Postgres (teal-prism) | Neon (LHR) | 🟢 ACTIVE | Credentials loaded in Portal. |

---

## 2. Codebase Summary & Completeness

### A. CVCE (Canonical Vedic Calculation Engine)
* **Location:** `cvce/` (Python 3.12, FastAPI)
* **Status:** Substantial, needs stabilization and GraphRAG wiring.
* **Key Achievements:** ~24 functional endpoints implementing core calculations (Astrology, Dashas, Yogas, KP, Varshaphala, Prashna). 7 golden tests passing.
* **Missing/Stalled:**
  - GraphRAG routes `/predict` transit house rules through `graph.json` when `CVCE_GRAPH_AS_RULES=1` (Phase 4); hardcoded `transit_rules.py` fallback when unset.
  - Ashtottari dasha via `/dashas` — fixed PyJHora response parsing (June 27).
  - Version Control: ✅ Unified monorepo at `github.com/mohanvenkateshai-blip/VedicAstro`.

### B. Portal (Web Application)
* **Location:** `portal/` (Next.js 16.2.x, React 19, Tailwind v4)
* **Status:** Substantial; auth/DB live in production.
* **Key Achievements:** 16 structured routes (chart entry at **`/vedicastro`**, not `/horoscope`), SVG KundaliChart, DashaDeepTree, and explorers for KP, Koota Milan, Varshaphala, Nakshatras, Bhava, Graha, Prashna, etc.
* **Missing/Stalled:**
  - Varshaphala gated to **pro** tier; free users redirected from `/chart/varshaphala`.
  - Desktop-suite items (30-cell worksheets, print profiles) remain out of web scope.
  - Version Control: ✅ Unified monorepo at `github.com/mohanvenkateshai-blip/VedicAstro`.

### C. Knowledge Graph (Rules & Citations Base)
* **Location:** `knowledge-graph/` (Python tools, JSON database)
* **Status:** **Production graph live — 4253 nodes, 5092 links, 28 hyperedges** (June 27).
* **Build pipeline:** `scripts/sync-gyan-to-raw.sh` → `scripts/gyan-corpus-extract.py` (deterministic, 29 `raw/*.md`) → `knowledge-graph/graphify-out/graph.json` → `scripts/sync-graph.sh --deploy` (Fly).
* **GraphRAG scope:** Citation enrichment **done**. Transit + muhurta rules from graph when `CVCE_GRAPH_AS_RULES=1` / `CVCE_GRAPH_AS_MUHURTA=1` — **done**. Engine wiring: `muhurta_rules_provider.py`, `muhurta_yogas.py`.
* **Gemini deep extract (graphify):** Partial. Paid billing enabled on AI Studio (`gen-lang-client-0385751724`). `gemini-3.5-flash` deep run hit **503 high-demand** on ~7/23 chunks; failed merges must **not** be deployed (prunes deterministic nodes). **35 manifest entries** still missing `semantic_hash` → safe to retry incrementally.
* **Stale artifact:** `cvce/data/graph.json` (448 nodes) — unused by runtime; remove or re-sync.
* **Version Control:** Large local diff **not committed** — see §6 below.

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

### Phase 5+: Feature Build-out & Integrations
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
- [ ] Kaksha transit calendar (A1 remainder), Chara/Kalachakra dashas, desktop §7 enhancements.

---

## 4. Known Issues & Tech Debts

1. **CVCE cold-start latency:** Scale-to-zero adds ~3–4s on first request after idle; not an outage.
2. **Documentation drift (reconciled June 27):** Root `README.md` and `portal/docs/feature-progress.json` now align with this file on CVCE offline status, `/vedicastro` route, and GraphRAG scope (enrichment vs rules source).
3. **Stale Paths in Docs:** Legacy scripts or local path references (e.g. `/home/claude/work`) left behind by previous tools.
4. **Transit citations (fixed June 27):** GraphInsights now collapses noisy graph metadata server- and client-side.
5. **Auth/DB (Phase 5):** Google OAuth + Neon + save/load/delete live. Tier limits enforced on save; Varshaphala requires pro.

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

## 6. Git, Vercel & Fly Deploy State (June 27)

| Surface | How it deploys | Current state |
|:---|:---|:---|
| **CVCE (Fly)** | `fly deploy` / `./scripts/sync-graph.sh --deploy` from local | **Live** — graph 4253 nodes; engine fixes deployed from **uncommitted** local files |
| **Portal (Vercel)** | Git push to `main` → Vercel build (typical) | **Partial** — Neon migrate + auth work on production; many Phase 5 portal files still **only local** (uncommitted) |
| **Git** | Manual `git commit` + `git push` | **`main` has large uncommitted diff** — agents do not auto-commit unless you ask |

**Handoff files:** `STATUS.md` (this file) + `CONTEXT.md` are the living handoff. Update both after major deploys; `CONTEXT.md` still shows legacy “277+ nodes” in topology diagram — reconcile when committing.
