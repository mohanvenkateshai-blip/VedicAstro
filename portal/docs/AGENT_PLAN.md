# VedicAstro — AI Agent Engineering Plan

## Team Activation (8 of 14 agents required for this scope)

| Agent | Role | Phase | Status |
|-------|------|-------|--------|
| 6 | Backend Systems Architect | 1 — Design CVCE endpoints | ⏳ |
| 1 | Full-Stack MVP Builder | 2 — Wire frontend to backend | ⏳ |
| 7 | Senior Frontend Engineer | 2 — Explorer components, charts | ⏳ |
| 14 | Knowledge & Intelligence Engineer | 2 — GraphRAG, classical rules | ✅ |
| 13 | DBA & Data Platform | 2 — Neon, encryption, RLS | ✅ |
| 9 | Security Auditor | 4 — CSP, Zod, input validation | ✅ |
| 2 | Codebase Auditor | 4 — SDLC compliance audit | ✅ |
| 11 | QA & Test Automation | 4 — CI, typecheck, test strategy | ✅ |
| 8 | Technical Lead | All — Orchestration | ✅ |

## Phase Plan

### Phase 1: Backend Engines (Agent 6)
**CVCE endpoints to build:**
1. `/special-points` — Mandi, Gulika, Bhrigu Bindu (PyJHora native)
2. `/dasha-deep` — Vimshottari 5-level (Pratyantar, Sookshma, Prana)
3. `/koota-match` — 36-point Guna Milan + Kuja Dosha + Vedha

### Phase 2: Frontend Components (Agents 1 + 7 + 14)
**New UI components:**
1. `NakshatraExplorer.tsx` — 27 nakshatra details, deities, lords, myths
2. `RashiExplorer.tsx` — 12 sign profiles, planetary behaviour
3. `DashaDeepTree.tsx` — 5-level Vimshottari recursive tree
4. `PushkarBadge.tsx` — Auto-flag planets in Pushkar navamsha
5. `SpecialPointsPanel.tsx` — Mandi, Gulika, Bhrigu Bindu display
6. `KootaMatcher.tsx` — Two-chart compatibility report

### Phase 3: Quality Gates (Agents 2, 9, 11)
All already completed.

## Dependency Graph
```
CVCE /dasha-deep ──────→ DashaDeepTree.tsx
CVCE /special-points ──→ SpecialPointsPanel.tsx
CVCE /koota-match ─────→ KootaMatcher.tsx
Static data ────────────→ NakshatraExplorer.tsx, RashiExplorer.tsx
CVCE /chart ────────────→ PushkarBadge.tsx (pushkarNavamsha flag)
```
