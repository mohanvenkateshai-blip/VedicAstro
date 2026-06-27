# VedicAstro — Living Status Document

This document is the **Single Source of Truth** for the current status, live health, and immediate roadmap of the VedicAstro project. For architectural principles, system topology, and immutable code guardrails, refer directly to `CONTEXT.md`.

*Last Updated: June 27, 2026 (Active Session: Phase 2 — CVCE recovery)*

---

## 1. Service Health & Deployments

| Component | Live URL / Connection | Hosted On | Status | Notes |
|:---|:---|:---|:---|:---|
| **Portal** | [portal-omega-two-10.vercel.app](https://portal-omega-two-10.vercel.app) | Vercel | 🟢 LIVE (HTTP 200) | UI is functional; Server-Side `/chart` renders will fail or degrade when CVCE is offline. |
| **CVCE (Engine)** | [vedicastro-cvce.fly.dev](https://vedicastro-cvce.fly.dev) | Fly.io (LHR) | 🔴 OFFLINE (HTTP 000) | Connection timeout (40s). Investigating in Phase 2 (cold start vs crashed/suspended). |
| **Muhūrta** | [muhurtha.uvwx.me](https://muhurtha.uvwx.me) | Fly.io (IAD) | 🟢 LIVE (HTTP 200) | **Frozen standalone.** Fully complete. Untouched per directive. |
| **Database** | Neon Postgres (teal-prism) | Neon (LHR) | 🟢 ACTIVE | Credentials loaded in Portal. |

---

## 2. Codebase Summary & Completeness

### A. CVCE (Canonical Vedic Calculation Engine)
* **Location:** `cvce/` (Python 3.12, FastAPI)
* **Status:** Substantial, needs stabilization and GraphRAG wiring.
* **Key Achievements:** ~24 functional endpoints implementing core calculations (Astrology, Dashas, Yogas, KP, Varshaphala, Prashna). 7 golden tests passing.
* **Missing/Stalled:**
  - GraphRAG is not wired as the rules source for `/predict` (currently using hardcoded `transit_rules.py`).
  - Ashtottari dasha calculations are missing (PyJHora lacks the module on Fly).
  - Version Control: ✅ Unified monorepo at `github.com/mohanvenkateshai-blip/VedicAstro`.

### B. Portal (Web Application)
* **Location:** `portal/` (Next.js 16.2.x, React 19, Tailwind v4)
* **Status:** Substantial, needs auth/DB integration and styling refinement.
* **Key Achievements:** 16 structured routes (chart entry at **`/vedicastro`**, not `/horoscope`), SVG KundaliChart, DashaDeepTree, and explorers for KP, Koota Milan, Varshaphala, Nakshatras, etc.
* **Missing/Stalled:**
  - Yogas page is a placeholder.
  - NextAuth is a null-session scaffold; Postgres and Row-Level Security are not integrated.
  - Version Control: ✅ Unified monorepo at `github.com/mohanvenkateshai-blip/VedicAstro`.

### C. Knowledge Graph (Rules & Citations Base)
* **Location:** `knowledge-graph/` (Python tools, JSON database)
* **Status:** Ingestion Complete (448 nodes, 1236 edges, 36 communities).
* **Key Achievements:** Fully ingested `Activity_Mapping.md` (91 activities), `Gochar_Phaladeepika_Pulippani.md`, `BPHS Vol 1`, and `Phaladeepika_Mantreswara.md`. Key finding: Rohiṇī identified as the central hub of the Muhurta network.
* **GraphRAG scope (important):** Citation enrichment via `PredictionEnhancer` is **done** (see `portal/docs/feature-progress.json` F01). Routing `/predict` rule selection through `graph.json` queries is **not done** — Phase 4 (F31).
* **Missing/Stalled:**
  - Version Control: ✅ Unified monorepo at `github.com/mohanvenkateshai-blip/VedicAstro`.

---

## 3. Active Roadmap (Phased Sequence)

We are strictly following a **phase-by-phase execution sequence with review gates**. Each phase requires user sign-off before proceeding.

### Phase 0: Consolidation & Clean-up (Completed)
- [x] Create `VedicAstro/STATUS.md` (this living document) as the single source of truth.
- [x] Archive fragmented handoffs from `Panchang/` and `portal/docs/` to `VedicAstro/docs/archive/`.
- [x] Relocate misplaced/untracked VedicAstro files and scripts out of the frozen Panchang repository to keep it purely untouched.
- [x] Align CONTEXT.md and verify all reference pointers.
- *Status:* **Completed.** Review gate passed.

### Phase 1: Unified Version Control Foundation (Completed)
- [x] Initialize `VedicAstro/` as a clean, single Git monorepo. Add a proper `.gitignore` and push to new remote `mohanvenkateshai-blip/VedicAstro`.
- [x] Separately, resolve the 5 modified files in the frozen `panchanga_muhurtha` repository (investigated diff, committed additive chart refactors, and pushed to origin).

### Phase 2: CVCE Recovery & Diagnostics
- [ ] Run Fly CLI diagnostics on the `vedicastro-cvce` app (logs, status, scaling configurations).
- [ ] Resolve the outage and ensure local + hosted tests pass.
- [ ] Verify that portal `/chart` displays live, precise coordinates from CVCE.

### Phase 3: Comprehensive Gap Analysis
- [ ] Build a formal `VedicAstro/docs/GAP_ANALYSIS.md` cross-referencing all 7 major systems and 51 enhancements from the professional Requirements document to map exact completeness (Done / Partial / Missing). This maps our long-term build-out plan.

### Phase 4: GraphRAG predicting
- [ ] Route the `/predict` endpoint rules to query the offline `graph.json` directly (via `graph_rag/graph.py` queries) instead of using the hardcoded `transit_rules.py` file.
- [ ] Retain hardcoded fallback with env-gate `CVCE_GRAPH_AS_RULES` for regression safety.

### Phase 5+: Feature Build-out & Integrations
- [ ] Implement and wire missing features mapped during the Phase 3 gap analysis (Yogas panel, Ashtottari dasha, animated transits, etc.).
- [ ] Integrate Postgres and database schema with Row-Level Security.
- [ ] Build NextAuth and proxy-layer RBAC (free/pro/premium/admin roles).

---

## 4. Known Issues & Tech Debts

1. **CVCE Connection Timeout:** Live engine at `vedicastro-cvce.fly.dev` is currently unreachable (Phase 2 target).
2. **Documentation drift (reconciled June 27):** Root `README.md` and `portal/docs/feature-progress.json` now align with this file on CVCE offline status, `/vedicastro` route, and GraphRAG scope (enrichment vs rules source).
3. **Stale Paths in Docs:** Legacy scripts or local path references (e.g. `/home/claude/work`) left behind by previous tools.
4. **Ashtottari Dasha Module Missing:** PyJHora on Fly lacks this.
5. **Transit Citations Verbose:** Citations require categorization on the enhancer-side.
6. **Auth/DB scaffold only:** NextAuth, Neon client, and save/load code exist but production RBAC + RLS are Phase 5+ (see F03–F05 in `feature-progress.json`).

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
