# Newbooks MD Ingest — 2026-06-29

## Ingested (12)
Copied from `Panchang/Gyan/newbooks/` → `knowledge-graph/raw/`, deterministic extract + Gemini batch (semantic).

| File | Notes |
|------|--------|
| Bhava_and_Graha_Balas_BVRaman_1996.md | |
| Crux_of_Vedic_Astrology_Timing_of_Events1.md | |
| Introduction_to_Vedic_Astrology_Sanjay_Rath.md | |
| Vedic_remedies_by_srath_pdf_free.md | |
| boney_marc_intricate_patterns_of_destiny_how_to_make_accurat.md | |
| jaimini_astrology_calculation_of_mandook_dasha_with_a_case_study_compress.md | |
| patel_cs_aiyar_cas_ashtakavarga.md | Distinct from `Ashtakavarga_System_Comprehensive_Handbook.md` |
| rath_s_jaimini_maharishis_upadesa_sutra.md | Distinct from `Jaimini_Sutras.md` |
| the_jyotish_digest_2005_volume_1_no_01_january_1.md | |
| the_jyotish_digest_2007_volume_3_no_04_november_1.md | |
| the_jyotish_digest_2009_volume_5_no_04_october_15.md | |
| wilhelm_ernst_classical_muhurta_jyotish.md | |

## Skipped duplicates (2)
See `newbooks-dedupe.json`.

| Skipped | Existing corpus |
|---------|-----------------|
| maharishi_parasaras_brihad_parasara_hora_sastra_vol_i.md | `Brihat_Parasara_Hora_Sastra_Vol_1.md` |
| maharishi_parasaras_brihad_parasara_hora_sastra_vol_ii.md | `Brihat_Parasara_Hora_Sastra_Vol_2.md` |

## Graph impact
- **Before:** 23,267 nodes / 35,438 links
- **After (deterministic):** 26,722 nodes / 38,881 links (+3,455 nodes)
- **Gemini semantic batch:** submitted 2026-06-29 (`batch/last-job.json`); merge when `JOB_STATE_SUCCEEDED`

## Pipeline
```bash
python3 scripts/ingest-newbooks-md.py
python3 scripts/gyan-corpus-extract.py
INGEST_ONLY_MD=... python3 scripts/gemini-batch-graph-extract.py submit|wait|merge
./scripts/sync-graph.sh --deploy
python3 scripts/supabase-corpus-sync.py --skip-gcp --graph-only --incremental
```
