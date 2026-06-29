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

### Architecture Pitfalls

- **Context Clash risk:** Python deployment patterns ≠ Next.js deployment patterns. CVCE goes on Fly.io (270MB image, writable FS for ephemeris). Portal goes on Vercel. Do not suggest Vercel for Python.
- **Graph OOM:** Deep BFS on the knowledge graph with no budget cap will exhaust memory. Always pass `--budget N` or `--dfs` for targeted queries.
- **Cusp precision:** Sidereal ascendant calculation uses PyJHora's internal PySwisseph — do not override or approximate it. The golden tests (Mohan's chart: Lagna Libra/Swati p4) validate precision.
- **PyJHora wall-clock convention:** PyJHora expects wall-clock local time + tz offset, NOT UTC. Converting to UTC before passing breaks house calculations.

---

## 6. Knowledge Graph & Corpus Vault (2026-06-29)

**Core Jyothisha (20 classical PDFs):**
- OCR/text → `raw/`: **20/20 complete**
- Graph extraction: **20/20 complete** — all books in production `graph.json` (23,267 nodes)
- Merged graph promoted to `graph.json` + `cvce/graph_rag/graph.json`; Fly deployed 2026-06-29

**Corpus vault (Supabase):**
- Tables: `corpus_sources`, `graph_nodes`, `graph_links`, `graph_ingest_runs` (RLS deny-all for clients)
- Storage: private bucket `corpus-vault` (markdown + graph snapshots)
- Sync: `scripts/supabase-corpus-sync.py`; wired as final step of `gcp-sync-results.sh`
- Portal admin: `/admin/knowledge` + `/api/admin/corpus/*` (service role, admin only)

**Production CVCE:**
- `graph.json` on Fly: **23,267 nodes** (promoted 2026-06-29 via `merge --promote` + `sync-graph.sh --deploy`)
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

## 8. Next Phases (in priority order)

1. **Supabase vault re-sync** — push 23k-node graph when network to Supabase is stable
2. **Vector embeddings** — `corpus_chunks` hybrid search (schema planned, not built)
3. **Kaksha calendar, Chara/Kalachakra dashas** — engine + UI
4. **Phase 13: LLM narration layer** — optional prose on `ReportFacts` (`CVCE_LLM_NARRATION=1`)

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
