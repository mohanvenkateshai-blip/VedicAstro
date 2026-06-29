# VedicAstro — Comprehensive Gap Analysis

**Created:** June 27, 2026 (Phase 3)  
**Sources:** [generic_vedic_astrology_software_features.md](Requirements/generic_vedic_astrology_software_features.md), [STATUS.md](../STATUS.md), [feature-progress.json](../portal/docs/feature-progress.json), CVCE `/orchestrate` manifest, portal routes, archived audits in [archive/](archive/)

**Legend:** ✅ Done · ⚠️ Partial · ❌ Missing

---

## Executive Summary

| Layer | Done | Partial | Missing | Notes |
|-------|------|---------|---------|-------|
| **7 major systems** (requirements §1–6) | 2 | 4 | 1 | Core calc + explorers strong; workspace/transits/yogas weak |
| **51 flagship enhancements** (§7) | 6 | 8 | 37 | Most are desktop-suite features out of web scope |
| **CVCE engine endpoints** | ~20 live | ~4 partial | ~6 | See §Engine coverage |
| **Portal routes** | 14 | 2 | 0 | Yogas + auth production wiring |
| **Classical rule accuracy** (audits) | ~40% | ~35% | ~25% | Engine-level gaps documented in audits |

**Honest platform completion:** ~65% shell/UI, ~45% classical calculation coverage, ~55% production readiness (post Phase 2 CVCE recovery).

**Critical path after this document:** Phase 4 (GraphRAG rules) → Phase 5+ items marked **P0/P1** below.

---

## Methodology

Each major system from the professional requirements directory is mapped against:

1. **CVCE** — FastAPI endpoints in `cvce/app/server.py`, `vedic_engine/`, `rules_engine/`
2. **Portal** — Next.js routes under `portal/src/app/`
3. **Audits** — June 2026 archived rule/calculation audits
4. **Feature tracker** — `portal/docs/feature-progress.json` (F01–F31)

Statuses:

- **Done** — End-to-end usable (API + UI where applicable), golden-tested or audit PASS
- **Partial** — Backend only, UI stub, audit PARTIAL/FAIL, or env-gated scaffold
- **Missing** — Not implemented or placeholder only

---

## 1. Advanced Transit Systems

| Feature | Status | Evidence |
|---------|--------|----------|
| Dynamic birth-to-transit mapping | ⚠️ Partial | `AnimatedTransitEngine`, `/predict`; overlay on natal chart in portal |
| Time-engine + dasha sync | ⚠️ Partial | `/dasha-deep`, DashaDeepTree; not fully synchronized with transit scrubber |
| Event series worksheets | ❌ Missing | No dedicated worksheet route |
| Animated transits engine | ✅ Done | F21, `/chart/transits`, CVCE `/predict` |
| Graphical ephemeris | ✅ Done | F22, portal component + CVCE positions |
| Kaksha & dasha calendars | ❌ Missing | Audit: Kaksha transit not implemented (`audit_ashtakavarga_muhurta.md`) |
| Time-of-transits search | ❌ Missing | No millisecond-precision search tool |
| Transit report / export | ⚠️ Partial | PDF export (F23); no chronological transit list generator |

**System verdict:** ⚠️ **Partial** — visual transit tools exist; micro-timing, Kaksha, and worksheet depth missing.

---

## 2. Core Workspace & User Interface

| Feature | Status | Evidence |
|---------|--------|----------|
| Multi-chart worksheets (30 cells) | ⚠️ Partial | Multi Varga View (F24); not 30-cell drag-drop grid |
| Cross-regional chart layouts | ✅ Done | North + South Indian in KundaliChart |
| Drag-and-drop cell arrangement | ❌ Missing | Fixed layouts only |
| Global layout themes | ⚠️ Partial | Light/dark + DESIGN.md tokens; no user skinning |
| Custom note-taking / client dossiers | ⚠️ Partial | Save/load scaffold (F05); no RLS production wiring |

**System verdict:** ⚠️ **Partial** — polished single-chart UX; not enterprise worksheet ecosystem.

---

## 3. Astrological Calculations & Divisional Charts (Vargas)

| Feature | Status | Evidence |
|---------|--------|----------|
| Complete Shodashvarga (D1–D60) | ✅ Done | CVCE `/chart`, schema, 7 golden tests |
| Shadbala & Bhava Bala | ⚠️ Partial | CVCE `/shadbala`; limited UI surfacing |
| Ashtakavarga grids (BAV/SAV) | ⚠️ Partial | SAV overlay in chart; Trikona Shodhana **FAIL** per audit |
| Panchang almanac | ⚠️ Partial | CVCE `/panchanga`; not continuous daily almanac UI |
| True vs mean nodes | ⚠️ Partial | Lahiri default; no fast-switch UI |
| Comprehensive ayanamsha library | ⚠️ Partial | LAHIRI in prod; others not exposed |

**System verdict:** ⚠️ **Partial** — D1–D60 core is strong; strength reductions and panchang depth incomplete.

---

## 4. Specialized Astrological Systems

| Feature | Status | Evidence |
|---------|--------|----------|
| KP System | ✅ Done | F25 (~90%), `/kp-system`, `/chart/kp` |
| Varshaphala (Tajika / solar return) | ✅ Done | F26, `/varshaphala`, CVCE endpoint |
| Muhurta engine | ⚠️ Partial | Frozen iframe to muhurtha.uvwx.me; no prop-driven fork |
| Koota / Guna Milan | ✅ Done | F14/F18, `/koota-match`, `/compatibility` |
| Prashna horary | ⚠️ Partial | CVCE `/prashna` stub; no one-click portal UX |

**System verdict:** ✅ **Mostly done** for KP, Varshaphala, compatibility; Muhurta integration deferred by design.

---

## 5. Built-In Interpretive Explorers

| Feature | Status | Evidence |
|---------|--------|----------|
| Graha explorer | ⚠️ Partial | Special points panel; not full graha isolation workbook |
| Bhava explorer | ❌ Missing | No dedicated house explorer route |
| Rashi explorer | ✅ Done | F16, `/learn/rashis` |
| Nakshatra explorer | ✅ Done | F15, `/learn/nakshatras` |

**System verdict:** ⚠️ **Partial** — learn/explore routes exist; graha/bhava deep-dive missing.

---

## 6. Comprehensive Dasha Systems

| Feature | Status | Evidence |
|---------|--------|----------|
| Vimshottari (5 levels) | ✅ Done | Audit PASS; `/dasha-deep`, DashaDeepTree |
| Yogini dasha | ⚠️ Partial | Audit FAIL on antardasha + balance (`audit_dasha_vargas.md`) |
| Ashtottari dasha | ⚠️ Partial | PyJHora gap on Fly; fallback in `/dashas` after server.py fix |
| Chara / Kalachakra / Shaddashika / Drig | ❌ Missing | Not in CVCE endpoint list |

**System verdict:** ⚠️ **Partial** — Vimshottari production-ready; alternative dashas incomplete.

---

## 7. Yoga Detection & Interpretation

| Feature | Status | Evidence |
|---------|--------|----------|
| Classical yoga detection engine | ⚠️ Partial | CVCE `/yogas`; audit: 14/34+ detected (`audit_yogas.md`) |
| Side-by-side yoga delineation UI | ❌ Missing | `/chart/yogas` = "Coming soon" placeholder |
| Nabhasa / Raja / Dhana / Adhi yogas | ⚠️ Partial | Many defined but **NOT IMPLEMENTED** in detection |

**System verdict:** ❌ **Missing at UI layer**; ⚠️ **Partial at engine layer** — P0 for Phase 5+.

---

## 8. Knowledge Graph & Prediction Intelligence

| Feature | Status | Evidence |
|---------|--------|----------|
| Graph ingestion (448 nodes) | ✅ Done | `knowledge-graph/graphify-out/graph.json` |
| GraphRAG citation enrichment | ✅ Done | F01, `PredictionEnhancer` |
| GraphRAG as `/predict` rules source | ❌ Missing | F31, Phase 4; hardcoded `transit_rules.py` today |
| Unified rules engine | ⚠️ Partial | F29 (70%); orchestrator exists, graph queries pending |

**System verdict:** ⚠️ **Partial** — data asset ready; intelligence routing is Phase 4.

---

## 9. Auth, Database & Production Hardening

| Feature | Status | Evidence |
|---------|--------|----------|
| Neon Postgres + encryption schema | ⚠️ Partial | F03 (60%); code in `portal/src/lib/db.ts`, `schema.sql` |
| Google OAuth / NextAuth | ⚠️ Partial | F04 (50%); null-session without env vars |
| Save/load charts + dashboard | ⚠️ Partial | F05 (70%); `/dashboard` not RBAC-gated in prod |
| RBAC (free/pro/premium/admin) | ❌ Missing | Phase 5+; `proxy.ts` seam not wired |

**System verdict:** ⚠️ **Partial** — scaffold only; Phase 5+ production target.

---

## 10. CVCE Engine Endpoint Coverage

| Endpoint | Status | Portal consumer |
|----------|--------|-----------------|
| `/health`, `/chart` | ✅ | Core `/vedicastro` |
| `/predict`, `/rules`, `/orchestrate` | ✅ | GraphInsights, explorers |
| `/dasha-deep`, `/dashas`, `/dasha` | ⚠️ | All Dashas Panel (Ashtottari partial) |
| `/kp-system`, `/varshaphala`, `/koota-match` | ✅ | Dedicated chart sub-routes |
| `/special-points`, `/shadbala`, `/yogas` | ⚠️ | Special page; yogas engine gaps |
| `/panchanga`, `/rahu-kalam`, `/prashna` | ⚠️ | Limited/no portal UX |
| `/chart.svg` | ✅ | F07, PDF export |
| `/cross-validate` | ✅ | Golden tests only |

---

## 11. Portal Route Coverage

| Route | Status | Notes |
|-------|--------|-------|
| `/`, `/vedicastro` | ✅ | Primary chart entry |
| `/chart/*` (dasha, transits, kp, varshaphala, special) | ✅ | 11-route architecture (F20) |
| `/chart/yogas` | ❌ | Placeholder stub |
| `/learn/nakshatras`, `/learn/rashis` | ✅ | Explorers |
| `/compatibility`, `/muhurta` | ✅ | iframe / matcher |
| `/dashboard`, `/auth/*` | ⚠️ | Env-gated scaffold |

---

## 12. Fifty-One Flagship Enhancements — Index

Full list in [Requirements doc](Requirements/generic_vedic_astrology_software_features.md) §7. Summary mapping:

| Category | Items | Done | Partial | Missing |
|----------|-------|------|---------|---------|
| OS / platform / licensing (1–3) | 3 | 0 | 1 | 2 |
| Ephemeris range & timezone (4, 29, 51) | 3 | 0 | 2 | 1 |
| Muhurta guards & chakras (5, 12–16, 32–33, 47) | 12 | 0 | 2 | 10 |
| UI/worksheet/print (6, 22–25, 35–46) | 18 | 2 | 4 | 12 |
| Advanced vargas/dashas (17–21, 25–28) | 9 | 1 | 3 | 5 |
| Yoga/transit visualizations (34, 36–37) | 3 | 1 | 1 | 1 |
| Database/search/branding (43–44, 48–50) | 4 | 0 | 1 | 3 |
| **Total** | **51** | **6** | **8** | **37** |

**Interpretation:** Most "51 enhancements" target a desktop flagship suite. VedicAstro intentionally scopes to web portal + hosted CVCE + frozen Muhurta iframe. **In-scope gaps** for Phase 5+ are items **34** (yoga delineation), **36–37** (transit timelines), **43–44** (chart DB search), not desktop OS optimization or 30-cell worksheets.

---

## 13. Audit-Driven Classical Gaps (Engine Accuracy)

Prioritized from archived audits — these affect **correctness**, not just UI:

### P0 — Critical

| ID | Gap | Source audit |
|----|-----|--------------|
| Y1 | 20+ yoga types defined but undetected (Raja, Dhana, Adhi, Nabhasa…) | `audit_yogas.md` |
| G1 | Moorthi Nirnaya house mapping wrong | `audit_panchanga_gochar.md` |
| G2 | Ketu omitted from Latta rules | `audit_panchanga_gochar.md` |
| D1 | Yogini antardasha + balance not implemented | `audit_dasha_vargas.md` |
| A1 | Trikona Shodhana / Kaksha transit missing | `audit_ashtakavarga_muhurta.md` |

### P1 — High

| ID | Gap | Source audit |
|----|-----|--------------|
| G3 | Tara exceptions (Vainasika, Janma restrictions) missing in Python | `audit_panchanga_gochar.md` |
| G4 | Kantaka Shani (Saturn 4th) check missing in `gochar.py` | `audit_panchanga_gochar.md` |
| D2 | Jaimini Chara Karakas not implemented | `audit_dasha_vargas.md` |
| Y2 | Kemadruma cancellation checks incomplete | `audit_yogas.md` |

### P2 — Medium (active items promoted)

- Wilhelm VTN muhurta yogas subset missing
- Pushkar Navamsha flagging, Bhrigu point, Mandi/Gulika enhancements
- D108, Tithi Pravesha, Dasha Pravesh charts

**Note (2026-06-29):** Previously deferred items (Vector embeddings, LLM narration, Kaksha+Chara/Kalachakra, deeper report polish) have been promoted to active P0/P1 per user directive. See STATUS.md and CONTEXT.md §9. Work started immediately.

---

## 14. Phase 5+ Prioritized Backlog

Ordered by impact × dependency alignment with roadmap:

| Priority | Work item | Phase | Depends on |
|----------|-----------|-------|------------|
| **P0** | Wire `/chart/yogas` UI to CVCE `/yogas` + fix detection gaps (Y1) | 5+ | — |
| **P0** | GraphRAG rules source for `/predict` (F31) | **4** | — |
| **P1** | Fix gochar rule discrepancies G1–G4 | 5+ | Phase 4 optional |
| **P1** | Yogini dasha antardasha + balance (D1) | 5+ | — |
| **P1** | Ashtakavarga Shodhana + Kaksha (A1) | 5+ | — |
| **P2** | Auth/DB/RBAC production wiring (F03–F05) | 5+ | User sign-off |
| **P2** | Jaimini Chara Karakas (D2) | 5+ | — |
| **P3** | Prop-driven Muhurta fork | deferred | Frozen constraint |
| **P3** | Desktop-suite enhancements (30-cell worksheets, etc.) | out of scope | — |

**Update 2026-06-29:** Vector embeddings on corpus_chunks, LLM narration (CVCE_LLM_NARRATION), Kaksha+Chara/Kalachakra dashas, and deeper Hiranya report UI polish promoted from deferred/later to active P0/P1. Implementation started in parallel.

---

## 15. Cross-Reference Index

| Document | Role |
|----------|------|
| [STATUS.md](../STATUS.md) | Live health + phase gates |
| [CONTEXT.md](../CONTEXT.md) | Architecture constitution |
| [feature-progress.json](../portal/docs/feature-progress.json) | Feature-level tracker |
| [chart_data.schema.json](chart_data.schema.json) | Canonical contract |
| [archive/audit_*.md](archive/) | Classical rule audits |
| [Requirements/generic_vedic_astrology_software_features.md](Requirements/generic_vedic_astrology_software_features.md) | Professional feature directory |

---

*Phases 0–4 complete. Phase 5+ backlog in [docs/GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md).*
