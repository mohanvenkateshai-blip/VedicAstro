# VedicAstro

The VedicShastra AI portal — a premium, accurate, rule-based Vedic Astrology
platform. Built in phases on top of a hardened Swiss-Ephemeris calculation core.

## Relationship to the standalone Muhurta module

The existing **standalone Muhurta module** (deployed at muhurtha.uvwx.me from
`…/04-UX-Practice/Panchang/panchanga_muhurtha`) is **frozen and untouched**. It
keeps its own deployment and its own tab. VedicAstro reuses the Muhurta module
only as a **prop-driven fork** (a later phase) that consumes shared horoscope
data — it has zero impact on, or dependency from, the standalone.

## Status — Phase 1: CVCE (complete + hosted)

| Component | State |
|-----------|-------|
| `cvce/` — Canonical Vedic Calculation Engine (FastAPI + PyJHora/Swiss Ephemeris) | ✅ built, golden-tested |
| `docs/chart_data.schema.json` — canonical horoscope contract | ✅ |
| Golden regression suite (reference charts + independent cross-check) | ✅ 7 passing |
| Containerization for hosting | ✅ Dockerfile |
| **Hosted on Fly.io** | ✅ live |

**Live engine:** https://vedicastro-cvce.fly.dev  (Fly app `vedicastro-cvce`, region `lhr`,
1 GB VM, scale-to-zero). Health: `GET /health`. Canonical chart: `POST /chart`.

```bash
curl -s https://vedicastro-cvce.fly.dev/chart -H 'content-type: application/json' \
  -d '{"birth_datetime":"1975-04-22T19:15:00","birth_lat":12.2958,"birth_lon":76.6394,"birth_tz":5.5,"name":"Mohan"}'
```

> Hosting note: the engine deploys to **Fly (container)**, not Vercel — its image is
> 270 MB (over Vercel's 250 MB function limit) and PyJHora needs a writable FS. The
> **portal** (Next.js) is the Vercel target. Redeploy: `cd cvce && fly deploy --remote-only --ha=false`.

See [`cvce/README.md`](cvce/README.md) to run and test the engine.

## Phase 2: Portal shell (complete)

`portal/` — Next.js 16 + React 19 + Tailwind v4, implementing `DESIGN.md`.
Server-renders horoscopes via the hosted CVCE (server-to-server); interactive
North/South Kundali, D1–D60 varga switcher, SAV overlay, planet table; light/dark.

**Live portal:** https://portal-omega-two-10.vercel.app  (`/horoscope` casts a chart).
Deployed to Vercel (project `portal`). See [`portal/README.md`](portal/README.md).

## Roadmap (later phases)

3. **Data layer** — PostgreSQL (`database_schema.sql`), `horoscopes.chart_data`
   stores the canonical payload; encryption + row-level security for birth PII.
4. **Auth/RBAC** — wire NextAuth + the `users` table into the `proxy.ts` seam
   (free/pro/premium/admin), gate `/dashboard` and `/admin`.
5. **Muhurta sub-module** — prop-driven fork of MuhurtaCosmos consuming `chart_data`.
6. **Prediction / knowledge-graph / evolution loop** — deferred; rule-based first,
   LLM only synthesizes (grounded, cited, expert-gated), with strong disclaimers.
7. **Optional:** a Python `/chart.svg` endpoint on CVCE for static contexts
   (PDF reports, OG/share images, email) — keeps the interactive React viewer for the app.

## Architecture (isolation guarantee)

```
04-UX-Practice/
  Panchang/panchanga_muhurtha/   FROZEN standalone — own deployment, own tab
  VedicAstro/                    THIS project
    cvce/                        calculation engine (Phase 1)
    docs/chart_data.schema.json  canonical contract
    portal/  modules/muhurta/    later phases (prop-driven fork)
```

Aligns with the bundle's High-Level Architecture Diagram
(`…/vedicshastra_master_bundle/High_Level_Architecture_Diagram.md`): CVCE is the
"Core Vedic Calculation Engine (pyswisseph + Custom Vedic Logic)" box. Per that
layering, **CVCE sits behind the portal's API + RBAC layer** — the browser never
calls it directly; the portal's server calls it server-to-server. So once the
portal exists, CVCE can be locked down to Fly **private networking (Flycast)**
and its public CORS allowlist tightened/removed.
