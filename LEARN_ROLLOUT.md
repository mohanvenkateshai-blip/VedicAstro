# VedicAstro — Learn Rollout Status (2026-07-01)

## Full Chapters

| Book | Chapters | Status | Evidence |
|------|----------|--------|----------|
| Rath JKRE | 10 | Complete | [Graphify output](knowledge-graph/graphify-out/rath-jkre.md) |
| Wilhelm Ernst Classical Muhurta | 12 | Complete | [Graphify output](knowledge-graph/graphify-out/wilhelm-ernst.md) |
| Vedic Remedies by Rath | 8 | Complete | [Graphify output](knowledge-graph/graphify-out/vedic-remedies.md) |
| Patel/Aiyar Ashtakavarga | 5 | Complete | [Graphify output](knowledge-graph/graphify-out/ashtakavarga.md) |
| Crux of Vedic Astrology | 7 | Complete | [Graphify output](knowledge-graph/graphify-out/crux-vedic-astrology.md) |
| Jyotish Digest volumes | 15 | Complete | [Graphify output](knowledge-graph/graphify-out/jyotish-digest.md) |

## Data Flows

| Component | Source | Destination | Status | Evidence |
|-----------|--------|------------|--------|----------|
| Knowledge Graph |  |  | Complete | [Graphify logs](knowledge-graph/logs/graphify-2026-07-01.log) |
| Corpus Vault |  | Supabase | Complete | [Sync logs](knowledge-graph/logs/supabase-sync-2026-07-01.log) |
| CVCE |  |  | Complete | [Sync script](scripts/sync-graph.sh) |

## Passing Tests

| Test Suite | Count | Status | Evidence |
|------------|-------|--------|----------|
| CVCE Golden Tests | 7 | Passing | [Test output](cvce/tests/golden/output-2026-07-01.log) |
| Portal Smoke Tests | 3/7 | Passing | [Test output](portal/tests/smoke/output-2026-07-01.log) |

## Deployment Status

| Component | Status | Evidence |
|-----------|--------|----------|
| CVCE | Deployed | [Fly.io logs](cvce/logs/fly-deploy-2026-07-01.log) |
| Portal | Stale | [Vercel logs](portal/logs/vercel-deploy-2026-07-01.log) |

## Next Steps

1. Push the updated graph to production
2. Deploy the portal to Vercel
3. Run full smoke tests on the portal
4. Monitor CVCE for any issues

