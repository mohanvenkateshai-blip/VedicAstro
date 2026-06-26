# VedicAstro — Session Handoff (2026-06-24)

State capture so a fresh session can continue with zero re-derivation. Durable
details also live in Claude memory (`vedicastro-architecture`,
`vedic-text-corpus`, `vedicastro-knowledge-graph`).

---

## TL;DR — what exists and is LIVE

| Layer | What | Where / URL | Status |
|-------|------|-------------|--------|
| **CVCE** (calc engine) | FastAPI + PyJHora/Swiss Ephemeris | https://vedicastro-cvce.fly.dev (Fly app `vedicastro-cvce`, region `lhr`, 1GB, scale-to-zero) | ✅ live, golden-tested |
| **Portal** | Next.js 16 + React 19 + Tailwind v4 | https://portal-omega-two-10.vercel.app (Vercel project **`vedicastro`**) | ✅ live |
| **Muhūrta tab** | the FROZEN standalone, embedded untouched | `/muhurta` iframes muhurtha.uvwx.me | ✅ live |
| **Knowledge graph** | graphify JKRE (277 nodes) | `VedicAstro/knowledge-graph/graphify-out/graph.json` | ✅ built |

Source tree: `04-UX-Practice/VedicAstro/` = `cvce/` (engine) + `portal/` (web) +
`knowledge-graph/` (JKRE) + `docs/chart_data.schema.json` (canonical contract).
The standalone `04-UX-Practice/Panchang/panchanga_muhurtha/` is **FROZEN — never edit**.

---

## Non-negotiable rules (locked with the user)

1. **Freeze the standalone.** The Muhūrta module stays its own full app, untouched;
   the portal's Muhūrta tab just **iframes** muhurtha.uvwx.me. The user does NOT want
   horoscope-sharing integration — fully standalone-in-a-tab is the intended end state.
2. **Engine→Fly, Portal→Vercel.** CVCE image is 270 MB (> Vercel's 250 MB function
   cap) and PyJHora needs a writable FS, so it can't go on Vercel.
3. **Accuracy:** hosted Swiss-Ephemeris only; no in-browser Keplerian fallback in the portal.
4. **Canonical contract** = `docs/chart_data.schema.json`; keep `cvce/app/chart.py`,
   `cvce/app/server.py:/chart`, and `portal/src/lib/types.ts` in lockstep.
5. **Design (anti-"AI-generic"):** Fraunces serif headings, Sora body, JetBrains mono;
   elevation by color + hairline, **no drop-shadows**; indigo + rare gold, never purple.
   Rules + drift log in `portal/DESIGN.md` — append on every drift.
6. **Token routing:** subagents → Haiku (rudimentary) / Sonnet (coding) / Opus (deep
   reasoning). Main session stays Sonnet. User is usage-conscious this week.
7. I **cannot** see the user's usage meter or toggle permission mode (Shift+Tab does that).

---

## Key files

- `cvce/app/{server,ephem,chart,config}.py` — `ephem.py` is the only PyJHora caller.
  `/chart` returns canonical chart_data. `/predict` = the prediction/Muhurta engine.
  Config via env (`CVCE_*`). Prod deps: `requirements-prod.txt` (KEEP `geocoder` —
  PyJHora hard-imports it; drops jyotishganit/skyfield). Redeploy: `cd cvce && fly deploy --remote-only --ha=false`.
- `cvce/tests/golden/` — 7 passing tests vs Mohan's real chart + jyotishganit cross-check.
- `portal/src/app/{page,vedicastro/page,muhurta/page}.tsx`, `components/chart/{KundaliChart,ChartViewer}.tsx`,
  `components/BirthForm.tsx` (place control = typeable + datalist + persists), `lib/cvce.ts` (server-only).
  Next 16: `proxy.ts` (not middleware), async `searchParams`, `turbopack.root` set. Redeploy: `cd portal && vercel --prod --yes`.
- `knowledge-graph/raw/` (staged sources) + `graphify-out/` (graph.json, graph.html, GRAPH_REPORT.md).

---

## Bugs fixed this session
- `cvce/vedic_engine/prediction/dasha.py`: `YOGINI_NAKSHATRA_MAP` NameError → use existing
  `_yogini_start()` helper. (Was crashing `/predict` whenever natal_signs were passed.)
- Portal place control reset after Compute → now a `name="place"` field that round-trips via URL.

---

## 💎 Documented finding (the user wants these "gems" captured)

**Rohiṇī is the empirical keystone of the muhūrta system.** In the knowledge graph,
`Rohini Nakshatra` is simultaneously the **#1 god node (15 edges)** and the **highest-
betweenness node (0.100)** — it bridges four otherwise-unrelated activity communities:
Business & Finance, Wedding & Panchāṅga, Muhūrta Scoring, and Saṁskāras & Learning.
The hyperedges show it's prescribed for both **Wedding (Vivāha)** and **Starting
Construction**, among others. *Why:* Rohiṇī is a Dhruva/Sthira (fixed) nakṣatra ruled
by the Moon (exalted in Rohiṇī's sign, Taurus) — the classical star of permanence and
auspicious establishment. The graph **quantifies** what the texts assert qualitatively:
across 91 activities spanning unrelated life-domains, Rohiṇī is the single most-
prescribed star. **Product angle:** surface "keystone nakṣatra" insights like this —
cross-domain auspicious stars users won't find on generic panchāṅga sites.
(Other latent gems flagged by the graph: Mars-in-7th ≈ Kantaka Saturn-in-7th; the
universal 3/6/11-from-Moon benefic-house rule; each planet's single worst transit house.)

> NOT YET RUN: the formal `/graphify query "Why does Rohini bridge…"` trace (~7k tokens),
> deferred at 92% usage. Run it next session to deepen + auto-save the answer into the graph.

---

## NEXT STEPS (in priority order)

1. **Finish the knowledge graph** (user: "don't leave anything midway"):
   - Activity_Mapping.md categories **13–23 + appendices** were NOT extracted (only ~1–12).
     Re-run extraction on that file (general-purpose subagent) → merge → `/graphify raw --update`.
   - Then add **BPHS** + **Phaladeepika** (in `Gyan/extracted_markdown/`) for natal yogas.
   - Run the **Rohiṇī query trace** and document any further gems in a `FINDINGS.md`.
2. **Wire `graph.json` into the prediction engine** as the rules source (GraphRAG retrieval),
   replacing/augmenting the hardcoded `vedic_engine` rules.
3. **Postgres + real auth/RBAC** (per `vedicshastra_master_bundle/database_schema.sql`):
   save charts per user; wire NextAuth into the `portal/src/proxy.ts` seam (free/pro/premium/admin);
   encrypt birth PII + row-level security.
4. Optional: Python `/chart.svg` endpoint on CVCE for static PDF/OG/email (keep React viewer for app).
5. Optional: rename Vercel default domain / disable Deployment Protection so the clean
   `vedicastro-*.vercel.app` URL is public (currently the short `portal-omega-two-10` alias is public).

---

## Verify-it-still-works checklist
- `curl https://vedicastro-cvce.fly.dev/health` → ok; `/chart` with Mohan returns schema-valid JSON.
- `cd cvce && .venv/bin/python -m pytest` → 7 golden pass.
- Portal `/vedicastro` renders Mohan's chart; `/muhurta` iframes the standalone.
- Standalone `panchanga_muhurtha/` unchanged (baseline shas in scratchpad earlier; 17/17 source files).
