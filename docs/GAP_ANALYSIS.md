# VedicAstro — Comprehensive Gap Analysis

**Created:** June 27, 2026 (Phase 3)  
**Last revised:** June 30, 2026 — aligned with Phases 2–5+ completion per [STATUS.md](../STATUS.md)  
**Sources:** [generic_vedic_astrology_software_features.md](Requirements/generic_vedic_astrology_software_features.md), [STATUS.md](../STATUS.md), [feature-progress.json](../portal/docs/feature-progress.json), CVCE `/orchestrate` manifest, portal routes, archived audits in [archive/](archive/)

**Legend:** ✅ Done · ⚠️ Partial · ❌ Missing

---

## Executive Summary

| Layer | Done | Partial | Missing | Notes |
|-------|------|---------|---------|-------|
| **7 major systems** (requirements §1–6) | 3 | 3 | 1 | Core calc + explorers + report strong; desktop worksheet depth out of scope |
| **51 flagship enhancements** (§7) | 8 | 8 | 35 | Most are desktop-suite features out of web scope |
| **CVCE engine endpoints** | ~22 live | ~3 partial | ~4 | Chara/Kalachakra dashas partial |
| **Portal routes** | 16 | 1 | 0 | Report depth still growing |
| **Classical rule accuracy** (audits) | ~55% | ~30% | ~15% | Phase 5+ audit fixes landed; residual yoga depth |

**Honest platform completion (June 2026):** ~75% shell/UI, ~55% classical calculation coverage, ~70% production readiness (CVCE live, auth/DB env-gated, GraphRAG rules on Fly).

**Critical path after this document:** Hiranya report polish, vector embeddings fill, residual audit P1 items — see §14.

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
| Prashna horary | ✅ Done | F37, `/prashna` page + CVCE `/prashna` |

**System verdict:** ✅ **Mostly done** for KP, Varshaphala, compatibility; Muhurta integration deferred by design.

---

## 5. Built-In Interpretive Explorers

| Feature | Status | Evidence |
|---------|--------|----------|
| Graha explorer | ✅ Done | F36, `/learn/grahas` |
| Bhava explorer | ✅ Done | F35, `/learn/bhavas` |
| Rashi explorer | ✅ Done | F16, `/learn/rashis` |
| Nakshatra explorer | ✅ Done | F15, `/learn/nakshatras` |

**System verdict:** ⚠️ **Partial** — learn/explore routes exist; graha/bhava deep-dive missing.

---

## 6. Comprehensive Dasha Systems

| Feature | Status | Evidence |
|---------|--------|----------|
| Vimshottari (5 levels) | ✅ Done | Audit PASS; `/dasha-deep`, DashaDeepTree |
| Yogini dasha | ✅ Done | Balance + antardasha fixed (Phase 5+ audit) |
| Ashtottari dasha | ✅ Done | PyJHora nested lord tuple parsing fixed |
| Chara / Kalachakra / Shaddashika / Drig | ⚠️ Partial | Kaksha + Chara/Kalachakra initial integration in `/dashas` |

**System verdict:** ⚠️ **Partial** — Vimshottari production-ready; alternative dashas incomplete.

---

## 7. Yoga Detection & Interpretation

| Feature | Status | Evidence |
|---------|--------|----------|
| Classical yoga detection engine | ⚠️ Partial | CVCE `/yogas`; audit: improved but not exhaustive |
| Side-by-side yoga delineation UI | ✅ Done | F32, `/chart/yogas` + `YogasPanel` |
| Nabhasa / Raja / Dhana / Adhi yogas | ⚠️ Partial | Detection gaps remain for rare yogas |

**System verdict:** ⚠️ **Partial at engine** — UI complete; rare yoga detection still expanding.

---

## 8. Knowledge Graph & Prediction Intelligence

| Feature | Status | Evidence |
|---------|--------|----------|
| Graph ingestion (26,722 nodes) | ✅ Done | `cvce/graph_rag/graph.json`, `newbooks-v1` on Fly |
| GraphRAG citation enrichment | ✅ Done | F01, `PredictionEnhancer` |
| GraphRAG as `/predict` rules source | ✅ Done | F31, `graph_rag/rules_provider.py`, `CVCE_GRAPH_AS_RULES=1` on Fly |
| Unified rules engine | ✅ Done | F29, orchestrator + graph rules with hardcoded fallback |

**System verdict:** ✅ **Done** — graph is production rules source with env-gated fallback.

---

## 9. Auth, Database & Production Hardening

| Feature | Status | Evidence |
|---------|--------|----------|
| Neon Postgres + encryption schema | ✅ Done | F03, `portal/src/lib/db.ts`, `schema.sql` |
| Google OAuth / NextAuth | ✅ Done | F04, env-gated; anonymous mode when unset |
| Save/load/delete charts + dashboard | ✅ Done | F05, `/dashboard` with tier save limits |
| RBAC (free/pro/premium/admin) | ✅ Done | F34, `proxy.ts` + `requireSession()` + Varshaphala pro gate |

**System verdict:** ✅ **Done in code** — production use requires Vercel env vars (`AUTH_SECRET`, `DATABASE_URL`, etc.).

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
| `/chart/yogas` | ✅ | YogasPanel + shadbala summary (F32) |
| `/chart/report` | ⚠️ | HoroscopeReport — 8 chapters; LLM narration optional |
| `/learn/nakshatras`, `/learn/rashis`, `/learn/jaimini` | ✅ | Explorers + classical reader |
| `/compatibility`, `/muhurta`, `/prashna` | ✅ | Matcher, iframe, horary |
| `/dashboard`, `/auth/*` | ✅ | Env-gated; proxy redirects when auth configured |

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

| Priority | Work item | Status | Notes |
|----------|-----------|--------|-------|
| ~~**P0**~~ | Wire `/chart/yogas` UI (F32) | ✅ Done | YogasPanel |
| ~~**P0**~~ | GraphRAG rules source (F31) | ✅ Done | Phase 4 |
| ~~**P1**~~ | Gochar rule fixes G1–G4 | ✅ Done | Phase 5+ audit fixes |
| ~~**P1**~~ | Yogini antardasha + balance (D1) | ✅ Done | |
| ~~**P1**~~ | Auth/DB/RBAC (F03–F05, F34) | ✅ Done | Env-gated |
| **P0** | LLM narration polish (`CVCE_LLM_NARRATION`) | In progress | Gate wired |
| **P0** | Vector embeddings fill on corpus_chunks | In progress | Schema + scripts landed |
| **P1** | Residual yoga detection (Y1 rare types) | Open | Not all 34+ yogas |
| **P1** | Jaimini Chara Karakas (D2) | Open | |
| **P2** | Prop-driven Muhurta fork | Deferred | Frozen constraint |
| **P3** | Desktop-suite enhancements | Out of scope | 30-cell worksheets, etc. |

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

*Phases 0–5+ core items complete. Residual backlog in §14. Live health: [STATUS.md](../STATUS.md).*
