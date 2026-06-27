# VedicAstro

The VedicShastra AI portal — a premium, accurate, rule-based Vedic Astrology
platform. Built in phases on top of a hardened Swiss-Ephemeris calculation core.

**Live status page:** https://portal-omega-two-10.vercel.app/status (probes Portal, CVCE, Muhūrta on each load)

**Living status (docs):** see [`STATUS.md`](STATUS.md) for roadmap, phase history, and the single source of truth for what is live vs pending.

## Relationship to the standalone Muhurta module

The existing **standalone Muhurta module** (deployed at muhurtha.uvwx.me from
`…/04-UX-Practice/Panchang/panchanga_muhurtha`) is **frozen and untouched**. It
keeps its own deployment and its own tab. VedicAstro reuses the Muhurta module
only as a **prop-driven fork** (a later phase) that consumes shared horoscope
data — it has zero impact on, or dependency from, the standalone.

## CVCE — Canonical Vedic Calculation Engine

| Component | State |
|-----------|-------|
| `cvce/` — FastAPI + PyJHora/Swiss Ephemeris | ✅ built, golden-tested |
| `docs/chart_data.schema.json` — canonical horoscope contract | ✅ |
| Golden regression suite (reference charts + independent cross-check) | ✅ 7 passing |
| Containerization for hosting | ✅ Dockerfile + `fly.toml` |
| **Hosted on Fly.io** | 🟢 **live** (scale-to-zero, ~3–4s cold start) |

**Engine URL:** https://vedicastro-cvce.fly.dev  (Fly app `vedicastro-cvce`, region `lhr`,
1 GB VM, scale-to-zero). Health: `GET /health`. Canonical chart: `POST /chart`.

```bash
curl -s https://vedicastro-cvce.fly.dev/chart -H 'content-type: application/json' \
  -d '{"birth_datetime":"1975-04-22T19:15:00","birth_lat":12.2958,"birth_lon":76.6394,"birth_tz":5.5,"name":"Mohan"}'
```

> Hosting note: the engine deploys to **Fly (container)**, not Vercel — its image is
> 270 MB (over Vercel's 250 MB function limit) and PyJHora needs a writable FS. The
> **portal** (Next.js) is the Vercel target. Redeploy: `cd cvce && fly deploy --remote-only --ha=false`.

See [`cvce/README.md`](cvce/README.md) to run and test the engine locally.

## Portal — Web application

`portal/` — Next.js 16 + React 19 + Tailwind v4, implementing `DESIGN.md`.
Server-renders horoscopes via CVCE (server-to-server when the engine is online);
interactive North/South Kundali, D1–D60 varga switcher, SAV overlay, planet table;
light/dark.

**Live portal:** https://portal-omega-two-10.vercel.app  — cast a chart at **`/vedicastro`**
(not `/horoscope`; that route name was retired). Deployed to Vercel (project `portal`).
See [`portal/README.md`](portal/README.md).

## Knowledge graph & GraphRAG scope

The offline knowledge graph (`knowledge-graph/graphify-out/graph.json`, ~448 nodes)
is **ingestion-complete**. GraphRAG powers **citation enrichment** (`PredictionEnhancer`)
and **transit house rules** for `/predict` when `CVCE_GRAPH_AS_RULES=1` (enabled on Fly).
Unset the env var to fall back to hardcoded `transit_rules.py` for regression safety.

## Roadmap (phased — see STATUS.md for detail)

| Phase | Focus | Status |
|-------|-------|--------|
| 0 | Consolidation & clean-up | ✅ Complete |
| 1 | Unified monorepo / version control | ✅ Complete |
| 2 | CVCE recovery on Fly.io | ✅ Complete |
| 3 | Formal gap analysis (`docs/GAP_ANALYSIS.md`) | ✅ Complete |
| 4 | GraphRAG as `/predict` rules source | ✅ Complete |
| 5+ | Feature build-out, Postgres + auth/RBAC | Pending |

Later integrations (not yet started): prop-driven Muhūrta fork, production
NextAuth + row-level security, optional `/chart.svg` for PDF/OG images.

Feature-level tracking: [`portal/docs/feature-progress.json`](portal/docs/feature-progress.json).

## Architecture (isolation guarantee)

```
04-UX-Practice/
  Panchang/panchanga_muhurtha/   FROZEN standalone — own deployment, own tab
  VedicAstro/                    THIS project
    cvce/                        calculation engine
    docs/chart_data.schema.json  canonical contract
    knowledge-graph/             offline graph artifact → CVCE /predict (Phase 4)
    portal/                      Next.js web app (Vercel)
```

Aligns with the bundle's High-Level Architecture Diagram
(`…/vedicshastra_master_bundle/High_Level_Architecture_Diagram.md`): CVCE is the
"Core Vedic Calculation Engine (pyswisseph + Custom Vedic Logic)" box. Per that
layering, **CVCE sits behind the portal's API + RBAC layer** — the browser never
calls it directly; the portal's server calls it server-to-server. Once CVCE is
healthy, it can be locked down to Fly **private networking (Flycast)** and its
public CORS allowlist tightened/removed.
