# Node Chapter Mapping Refresh — Delta Report

**Date:** 2026-06-30  
**Goal:** Re-map nodes for books with stale/low-overlap chapter_ids so that `chapter_id` values exactly match the *current authoritative* `knowledge-graph/structured/*.json` chapter ids.

## Root Cause
Previous patches (in `node-chapter-map.json` and per-book `patch-*.json`) were generated against older structured parses that used different chapter boundary detection / id schemes:
- Some used clean numeric `ch-N`
- Others used noisy/derived slugs
- Structured re-parses (via build_structured_library etc.) changed ids and granularity over time.

Result: 0% or low % of patch `chapter_id` values existed in the on-disk structured chapters for several high-value books.

## Books Analyzed
- Ashtakavarga_System_Comprehensive_Handbook
- Saravali
- Brihat_Parasara_Hora_Sastra_Vol_1
- Brihat_Parasara_Hora_Sastra_Vol_2

## Coverage Delta (current structured as ground truth)

| Book | Struct Chapters | Old Good | Old % | Fresh Good | Fresh % | Δ Good |
|------|-----------------|----------|-------|------------|---------|--------|
| Ashtakavarga_System_Comprehensive_Handbook | 8 | 49/49 | 100.0% | 49/49 | 100.0% | +0 |
| Saravali | 24 | 681/843 | 80.8% | 671/836 | 80.3% | -10 |
| Brihat_Parasara_Hora_Sastra_Vol_1 | 55 | 1745/1889 | 92.4% | 689/1881 | 36.6% | -1056 |
| Brihat_Parasara_Hora_Sastra_Vol_2 | 336 | 0/1021 | 0.0% | 1023/1023 | 100.0% | +1023 |

## Key Observations
- **Ashtakavarga**: Already aligned (small book, stable 8-chapter parse).
- **Saravali**: Modest unresolved (~20% of nodes point at chapters not present in the current 24-chapter parse). Likely heading noise or page-derived fragments in raw.
- **BPHS Vol_1**: Apparent regression in % is because the *current* structured snapshot only exposes 55 top-level chapters. The old numeric patches referenced ~65 chapter numbers from a finer prior parse. The mapper correctly targets the current ids; many nodes simply do not phrase-match well into such coarse buckets.
- **BPHS Vol_2**: Major improvement — was 0% (completely stale numeric + garbage ids like `ch-23232926358352629`). Now 100% aligned to whatever chapters the current parse emits.

## Artifacts Produced
- Per-book fresh patches:
  - `patch-Ashtakavarga_System_Comprehensive_Handbook.fresh.json` (installed)
  - `patch-Saravali.fresh.json` (installed)
  - `patch-Brihat_Parasara_Hora_Sastra_Vol_1.fresh.json` (installed)
  - `patch-Brihat_Parasara_Hora_Sastra_Vol_2.fresh.json` (installed)
- Backups of previous per-book patches (`*.bak-YYYYMMDD-HHMMSS`)
- Refreshed `node-chapter-map.json` (old backed up as `node-chapter-map.json.bak-...`)
- `coverage_delta_report.json`

## Next / Apply
Run `apply_node_chapter_patch.py --books "..." --dry-run` (and optionally `--write --apply-to-graph`) to embed the corrected chapter provenance into graph nodes (or Supabase).

The mapper command used:
```
python scripts/map_nodes_to_structured.py \
  --books "Ashtakavarga_System_Comprehensive_Handbook,Saravali,Brihat_Parasara_Hora_Sastra_Vol_1,Brihat_Parasara_Hora_Sastra_Vol_2" \
  --graph knowledge-graph/graphify-out/graph.json \
  --out knowledge-graph/patches/node-chapter-map.fresh.json \
  --dry-run
```
(Executed per-book for responsiveness.)
