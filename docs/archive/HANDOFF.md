# VedicAstro — Handoff v3.5 · 2026-06-26

## Quick Start
```bash
# Portal
cd portal && npm run dev              # http://localhost:3000
cd portal && npm run build && vercel --prod --yes   # deploy

# CVCE
cd cvce && fly deploy --app vedicastro-cvce

# Verify
curl https://vedicastro-cvce.fly.dev/health
curl https://vedicastro-cvce.fly.dev/orchestrate/health
curl https://portal-omega-two-10.vercel.app
```

## Deployments
| Service | URL | Platform | Status |
|---------|-----|----------|--------|
| Portal | https://portal-omega-two-10.vercel.app | Vercel | ✅ |
| CVCE | https://vedicastro-cvce.fly.dev | Fly.io LHR | ✅ |
| Muhurta | https://muhurtha.uvwx.me | Fly.io IAD | ✅ Frozen |
| Database | neon-teal-prism | Neon LHR | ✅ |

## Routes (11 total)
| Route | Engine | Component | Status |
|-------|--------|-----------|--------|
| / | — | Landing page | ✅ |
| /chart | Janma Kundali | ChartViewer + GraphInsights | ✅ |
| /chart/transits | Gochar Phala | AnimatedTransit + Ephemeris | ✅ |
| /chart/dasha | Dasha Phala | DashaDeepTree + AllDashas | ✅ (Vim ✅, Yog ✅, Ash ⚠️) |
| /chart/yogas | Yoga Phala | Placeholder | ⚠️ |
| /chart/special | Special Points | SpecialPointsPanel | ✅ |
| /chart/kp | KP System | KPExplorer | ✅ |
| /chart/varshaphala | Varshaphala | VarshaphalaPanel | ✅ |
| /compatibility | Koota Milan | KootaMatcher | ✅ |
| /learn/nakshatras | Shastra Pramana | NakshatraExplorer | ✅ |
| /learn/rashis | Shastra Pramana | RashiExplorer | ✅ |
| /dashboard | Auth+DB | Saved charts | ✅ |
| /muhurta | Muhurta Nirnaya | iframe standalone | ✅ |
| /vedicastro | Legacy | All-in-one page | ✅ |

## Env Vars (Vercel)
| Key | Set | Purpose |
|-----|-----|---------|
| CVCE_BASE_URL | ✅ | https://vedicastro-cvce.fly.dev |
| AUTH_SECRET | ✅ | |
| AUTH_GOOGLE_ID | ✅ | |
| AUTH_GOOGLE_SECRET | ✅ | |
| DATABASE_URL | ✅ | Neon Postgres |
| ENCRYPTION_KEY | ✅ | AES-256 PII |

## Known Issues
| Bug | Status |
|-----|--------|
| Ashtottari dasha: None | PyJHora on Fly.io lacks module |
| Yogas tab: placeholder | Needs shadbala/yogas component wiring |
| CVCE cold start: 5-15s | Scale-to-zero, first request slow |
| Transit citations: verbose | Needs enhancer-side categorization |

## Engines (8)
| # | Name | Endpoint | Keywords |
|---|------|----------|----------|
| 1 | Janma Kundali | /chart | chart, kundali, horoscope |
| 2 | Gochar Phala | /predict | transit, today, prediction |
| 3 | Dasha Phala | /dashas | dasha, period, vimshottari |
| 4 | Yoga Phala | /yogas | yoga, combination |
| 5 | Bala Nirnaya | /shadbala | strength, dignity |
| 6 | Muhurta Nirnaya | standalone | auspicious, election |
| 7 | Koota Milan | /koota-match | compatibility, matching |
| 8 | Shastra Pramana | /rules/query | citation, source |
