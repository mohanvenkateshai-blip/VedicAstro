# VedicAstro Portal

The web portal for VedicShastra AI — Next.js 16 (App Router) + React 19 +
Tailwind v4, implementing the `DESIGN.md` system. Server-renders horoscopes by
calling the hosted **CVCE** engine; deployed to Vercel.

**Live:** https://portal-omega-two-10.vercel.app  ·  `/vedicastro` casts a chart.

## Architecture

```
browser ──> portal (Next.js, Vercel) ──server-to-server──> CVCE (FastAPI, Fly)
                                                            https://vedicastro-cvce.fly.dev
```

The browser never calls CVCE directly — only the portal's server does
(`src/lib/cvce.ts`, marked `server-only`). The canonical `chart_data` shape is
mirrored in `src/lib/types.ts` (kept in lockstep with
`../docs/chart_data.schema.json`).

## Key files

```
src/
  app/
    page.tsx              landing (premium/calm, per DESIGN.md)
    vedicastro/page.tsx    birth form + server-rendered chart (defaults to a demo)
    layout.tsx            header, fonts, theme (no-flash), footer
    globals.css           DESIGN.md tokens (light + dark via .dark)
  components/
    chart/KundaliChart.tsx   prop-driven N/S SVG kundali (renders any varga)
    chart/ChartViewer.tsx    N/S toggle, D1–D60 selector, SAV overlay, planet table
    BirthForm.tsx            place presets + birth fields (GET → shareable URL)
    SiteHeader.tsx, ThemeToggle.tsx, ui/{Button,Card}.tsx
  lib/
    cvce.ts               server-only client for the engine
    cvce-client.ts        browser-safe CVCE proxy client (via /api/cvce/*)
    types.ts              ChartData TS mirror of the canonical contract
    auth/                 NextAuth v5 + Google OAuth, encryption, RLS schema
    db.ts                 Neon Postgres (env-gated)
  proxy.ts                Next 16 edge proxy — gates /dashboard and /admin when auth configured
```

## Develop

```bash
npm install
npm run dev          # http://localhost:3000
```

Optional env (defaults to the live engine if unset):

```bash
CVCE_BASE_URL=https://vedicastro-cvce.fly.dev

# Auth + database (anonymous mode when unset)
AUTH_SECRET=...
AUTH_GOOGLE_ID=...
AUTH_GOOGLE_SECRET=...
DATABASE_URL=postgresql://...
ADMIN_EMAILS=you@example.com
```

## Deploy

```bash
vercel --prod        # from this directory (project: "portal")
```

## Reuse note

The Kundali chart components here are an independent, prop-driven **fork** of the
geometry first built for the frozen standalone — they consume `chart_data` and
share no code with `…/Panchang/panchanga_muhurtha`. The Muhurta sub-module (a
later phase) follows the same freeze-and-fork pattern.
