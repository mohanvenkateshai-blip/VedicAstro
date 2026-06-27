# VedicAstro — AI Context Constitution

**Read this file before writing any code or making any architectural decision.**
It is the single source of truth for system topology, immutable constraints, and hard-won lessons.

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
              │  Knowledge Graph (offline artifact)   │
              │  knowledge-graph/graphify-out/        │
              │  graph.json — 4253 nodes, 5092 links   │
              │  → future: wired into /predict        │
              └──────────────────────────────────────┘
```

**Three distinct codebases that NEVER share imports, processes, or ports:**

| Component | Location | Runtime | Deploy |
|-----------|----------|---------|--------|
| CVCE (engine) | `cvce/` | Python 3.12 / FastAPI | Fly.io (`vedicastro-cvce`, region `lhr`) |
| Portal | `portal/` | Next.js 16.2.x / React 19 | Vercel (project `vedicastro`) |
| Muhūrta Standalone | `Panchang/panchanga_muhurtha/` | In-browser Babel React | Fly.io separate app + Panchang Vercel |
| Knowledge Graph | `knowledge-graph/` | Offline build artifact | N/A — consumed by CVCE `/predict` |

---

## 2. Immutable Guardrails (NEVER violate)

### Architecture
- **The Muhūrta standalone is FROZEN.** `Panchang/panchanga_muhurtha/` is byte-for-byte frozen. Never edit it. The portal's `/muhurta` tab is ONLY an `<iframe src="muhurtha.uvwx.me">` — nothing else.
- **Accuracy = hosted Swiss-Ephemeris only.** No in-browser Keplerian fallback. No approximate calculations. PyJHora + sidereal Lahiri ayanamsa only.
- **Canonical contract = `docs/chart_data.schema.json`.** `cvce/app/chart.py`, `server.py:/chart`, and `portal/src/lib/types.ts` MUST stay in lockstep with this schema. Change the schema → change all three simultaneously.
- **Browser never hits CVCE directly.** `portal/src/lib/cvce.ts` is `server-only`. All CVCE calls are server-side Next.js fetches.
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
- `lib/auth.ts` is currently a scaffold (returns null session) — do not wire it until Postgres phase

### When working on Knowledge Graph
- Source files live in `knowledge-graph/raw/`
- Output in `knowledge-graph/graphify-out/` — do not edit `graph.json` manually
- Python interpreter: `$(cat knowledge-graph/graphify-out/.graphify_python)`
- Extraction chunks: `.graphify_chunk_01.json` (cats 1-12, Activity_Mapping), `.graphify_chunk_02.json` (Gochar_Phaladeepika), `.graphify_chunk_03.json` (cats 13-23 + appendices, Activity_Mapping) — chunk_03 may still be in progress
- To extend: add files to `raw/`, then run `/graphify raw --update`, then `./scripts/sync-graph.sh`
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

### Architecture Pitfalls

- **Context Clash risk:** Python deployment patterns ≠ Next.js deployment patterns. CVCE goes on Fly.io (270MB image, writable FS for ephemeris). Portal goes on Vercel. Do not suggest Vercel for Python.
- **Graph OOM:** Deep BFS on the knowledge graph with no budget cap will exhaust memory. Always pass `--budget N` or `--dfs` for targeted queries.
- **Cusp precision:** Sidereal ascendant calculation uses PyJHora's internal PySwisseph — do not override or approximate it. The golden tests (Mohan's chart: Lagna Libra/Swati p4) validate precision.
- **PyJHora wall-clock convention:** PyJHora expects wall-clock local time + tz offset, NOT UTC. Converting to UTC before passing breaks house calculations.

---

## 6. Knowledge Graph State

**Current graph** (as of 2026-06-25): 448 nodes, 1236 edges, 36 communities.

**Sources ingested (all 4 sources complete):**
- `Activity_Mapping.md` — all 91 activities, 20 categories (chunks 01 + 03)
- `Gochar_Phaladeepika_Pulippani.md` — full transit text (chunk 02)
- `Brihat_Parasara_Hora_Sastra_Vol_1.md` — natal yogas, planet characteristics (chunk 04)
- `Phaladeepika_Mantreswara.md` — Pancha Mahapurusha yogas, Neecha Bhanga types, Yogakaraka-by-ascendant, Ashtakavarga (chunk 05)

**Key new communities (added 2026-06-25):**
- Com 3 — Natal Yogas & Ashtakavarga (43 nodes): yogas, Neecha Bhanga, Kendradhipati Dosha
- Com 4 — Planetary Natures & Dignities (38 nodes): all 9 planets with full BPHS attributes
- Com 7 — Named Special Yogas (16 nodes): Amala, Lakshmi, Khadaga, Chamara, etc.

**Cross-text conflict encoded:** Mantreswara's Viparita Raja Yoga (Harsha/Sarala/Vimala) contradicts Parasara — `phaladeepika_yoga_viparita_raja --contradicts--> bphs_principle_trik_weakness`. Flag this ambiguity in the prediction engine.

**Sources NOT YET ingested:**
- BPHS Vol 2 (optional, lower priority)
- Muhurta Chintamani (referenced as stub, rules not ingested)

**Key finding — Rohiṇī is the empirical keystone nakshatra:**
Highest betweenness (0.100) + most edges (15) in the graph. Bridges Business & Finance, Wedding & Panchāṅga, Muhūrta Scoring, and Saṁskāras. Prescribed across both Wedding (Vivāha) and Construction — qualitatively different domains — because it is a Dhruva/Sthira (fixed) nakshatra ruled by the Moon (exalted in Taurus). The graph *quantifies* what texts assert qualitatively. Document more such gems in `knowledge-graph/graphify-out/FINDINGS.md`.

---

## 7. Token Routing

| Task | Model |
|------|-------|
| Deep reasoning, architecture, cross-domain analysis | Opus |
| Coding (Python, TypeScript, components) | Sonnet |
| Rudimentary extraction, simple file ops | Haiku (subagents) |

---

## 8. Next Phases (in priority order)

1. **Knowledge graph — COMPLETE** ✅ (448 nodes, 1236 edges, 4 sources ingested, FINDINGS.md has Finding 01)
2. **Wire graph.json into `/predict`** as GraphRAG rules source (replaces hardcoded `vedic_engine` rules)
3. **Postgres + real auth/RBAC** — NextAuth + `users` table + encrypt birth PII + RLS + wire into `proxy.ts` seam (free/pro/premium/admin)
4. Optional: Python `/chart.svg` endpoint on CVCE for static PDF/OG/email
5. Optional: Fix Vercel Deployment Protection for clean public URL

---

## 9. Verify-It-Still-Works Checklist

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
