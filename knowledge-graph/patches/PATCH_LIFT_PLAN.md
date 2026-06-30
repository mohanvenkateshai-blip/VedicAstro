# PATCH_LIFT_PLAN (node-to-chapter provenance)

Generated: 2026-06-30 (shell/data sub-agent, read-only probes + local drys; no Supabase writes performed)

## Safe Invocations

Local graph dry (no side effects):
```
python3 scripts/apply_node_chapter_patch.py --books "Jaimini_Sutras,Saravali" --dry-run --graph knowledge-graph/graphify-out/graph.json
```

Local graph write (creates timestamped .bak next to graph.json):
```
python3 scripts/apply_node_chapter_patch.py --books "..." --graph knowledge-graph/graphify-out/graph.json --apply-to-graph --write
```

Supabase dry (compute only; supports --dry-run --supabase):
```
python3 scripts/apply_node_chapter_patch.py --books "Phaladeepika_Mantreswara,Jaimini_Sutras" --supabase --dry-run --limit-samples 4
```

Supabase write (live; requires --write and not --dry-run):
```
python3 scripts/apply_node_chapter_patch.py --books "Phaladeepika_Mantreswara" --supabase --write
```

--books: comma-separated stems (no .json). --patch to override source map. --limit-samples for fewer before/after examples.

## Full Local Graph Dry-Run (current patch vs knowledge-graph/graphify-out/graph.json)

- nodes loaded: 26722
- patches loaded: 16353
- matched: 16353
- applied (would-update): 4480
- skipped (idempotent equivalent): 11873
- books touched: 18
- would-write count: 4480

Books in patch (patch counts): Brihat_Parasara_Hora_Sastra_Vol_1:1881, Phaladeepika_Mantreswara:1445, Hora_Sara:1252, Brihat_Samhita:1201, Phaladeepika_English_Translation:1200, Sarvartha_Chintamani:1181, Brihat_Parasara_Hora_Sastra_Vol_2:1023, Gochar_Phaladeepika_Pulippani:982, Saravali:836, Deva_Keralam_2:795, Deva_Keralam_1:775, Prasna_Marga_Part_1:767, Jaimini_Sutras:676, Jataka_Tatva_Mahadeva:642, Uttara_Kalamrita:638, Brihat_Jataka:527, Jataka_Parijata:483, Ashtakavarga_System_Comprehensive_Handbook:49.

## Supabase Live Baseline (probes + targeted id fetches; newbooks-v1)

- Total graph_nodes: 26722
- Broad sample (~1000): chapter_id present = 160 (~16%)
- Per-stem chapter presence (source_file ilike, ~300 sample):
  - Jaimini: ~2277 total nodes, ~7% with chapter
  - Saravali: ~843 total, 100%
  - Hora_Sara: ~1278, ~99%
  - Jataka_Tatva: ~739, ~95%
  - BPHS (Vol1+Vol2): ~2913, 100%
  - Ashtakavarga: ~423 total, ~16% (matches patch count 49)
  - Prasna_Marga: ~1549, ~6%
  - Phaladeepika (broad ilike): ~3781 total, 0% in sampled slice

Patch target node_id resolution + would-update on Supabase (by-id fetch of exact patch entries):
- Jaimini_Sutras (676 patches): 674 nodes resolved on Supabase (by-id); all lacked patch_method → 674 stampable (2 patch node_ids absent from current Supabase graph)
- Saravali (836): 836 fetched; equivalent
- Phaladeepika_English_Translation (1200): 1200 fetched; equivalent
- Phaladeepika_Mantreswara (1445): 1445 fetched; 0 ch on targets → 1445 would set chapter
- Prasna_Marga_Part_1 (767): 767 fetched; equivalent
- BPHS Vol1 (1881) / Vol2: ids aligned in prior checks; high overall presence
- Ashtakavarga (49): ids resolved; coverage accounts for observed 49 with chapter
- Brihat_Samhita (1201): only 350 patch node_ids exist in Supabase (others orphaned vs current ids); the 350 are already set
- Deva_Keralam_1 (775), Hora_Sara (1252): 0 patch node_ids resolved (no lift from this patch file; ch% for Hora high via other path)

Note: node_ids in the patch were produced against a local graph snapshot. Where Supabase node ids differ (re-ingest, variants, additional sources), patches are inert for those entries.

## Before/After Samples (2-3 high-value + 1 illustrative)

Local graph (one of the 4480 would-updates; Gochar):
- node: gochar_phaladeepika_pulippani_book
- before: chapter_id=None, match_method=None (props empty or minimal)
- after (injected): chapter_id='ch-gochar_phaladeepika', hierarchy_path='GOCHAR PHALADEEPIKA', match_method='phrase_lookup', patch_method='phrase_lookup', confidence=0.92, patch_conf=0.92, review_needed=False (plus matched_on etc per patch)

Supabase Jaimini (stamp of provenance markers; 676 in patch file, 674 resolved on Supabase):
- node: gyan_jaimini_sutras_corpus (and sec_page_*)
- before: chapter_id='ch-132', match_method='phrase_lookup', confidence=0.92, patch_method absent (also review_needed absent)
- patch target: chapter_id='ch-132', method='phrase_lookup', confidence=0.92, review_needed=True, book_id='Jaimini_Sutras'
- after (stamp via edit): same core ch+method+conf + patch_method='phrase_lookup', patch_conf=0.92, review_needed=True, matched_on, book_id etc.

Supabase Phaladeepika_Mantreswara (largest direct chapter lift observed):
- node: phaladeepika_concept_text
- before: chapter_id=None, match_method=None
- patch: chapter_id='ch-english_translation_commentary', method='phrase_lookup', ...
- after: chapter_id set + match/patch_method + confidence + review_needed + hierarchy if present in patch entry
- node: phaladeepika_concept_pancha_mahapurusha
- before: None
- patch: chapter_id='ch-chapter_6_yogas'
- after: chapter set as above

## LIFT PLAN: books + order (high-visibility / Learn first)

Apply order prioritizes: (a) observed would-update on Supabase patch targets, (b) high-visibility classics used by Learn/portal (Jaimini, BPHS, Saravali, Phaladeepika, Ashtakavarga), (c) books where patch ids align so the apply script can act.

1. Phaladeepika_Mantreswara — 1445 chapter assignments expected. Largest measurable ch lift from current patches.
2. Jaimini_Sutras — 676 stamps (patch_method / review flags). Overall book coverage remains partial (~676/2277 nodes) due to structured chapter quality; still high-vis + weak per probes.
3. Saravali — stamps; already strong ch% (reference quality).
4. Brihat_Parasara_Hora_Sastra_Vol_1 + Vol_2 — core; confirm stamps / any delta.
5. Ashtakavarga_System_Comprehensive_Handbook — small set (49), currently ~16% overall; stamp/verify.
6. Phaladeepika_English_Translation — stamps.
7. Prasna_Marga_Part_1 — stamps (book overall low %; patch targets covered).
8. Remaining with alignment (Jataka_Parijata, Uttara_Kalamrita, Brihat_Jataka, Sarvartha_Chintamani, Gochar...).
9. Deva_Keralam_*, Hora_Sara, Brihat_Samhita (partial) — current patch node_ids largely do not resolve; expect 0 or low effect. Coverage for these arrived via other means. Re-map using live Supabase nodes if full provenance desired.

Expected global chapter % movement: modest (adds the Phal_Mant 1445 + stamps on others). The bulk of "missing" chapters (Jaimini long tail, Prasna, Ashtak overall, Phal variants) are nodes without patch entries. Further lift requires mapper/structured improvements.

## Exact Next Commands (run drys, then selective writes)

```
# Local snapshot dry (full or targeted)
python3 scripts/apply_node_chapter_patch.py --books "Phaladeepika_Mantreswara,Jaimini_Sutras,Brihat_Parasara_Hora_Sastra_Vol_1" --dry-run --graph knowledge-graph/graphify-out/graph.json --limit-samples 4

# Supabase dry for top lift book (post-edit: expects applied ~1445)
python3 scripts/apply_node_chapter_patch.py --books "Phaladeepika_Mantreswara" --supabase --dry-run --limit-samples 3

# Supabase dry for Jaimini (clean full run post-edit: 676 patches, 674 nodes resolved, applied=674 stamps, skipped=0, upsert_targets=674; samples emitted; 2 node_ids did not resolve in Supabase)
python3 scripts/apply_node_chapter_patch.py --books "Jaimini_Sutras" --supabase --dry-run --limit-samples 2

# Optional: bring committed local graph.json up to date with all patches (backs up first)
python3 scripts/apply_node_chapter_patch.py --books "Ashtakavarga_System_Comprehensive_Handbook,Brihat_Jataka,Brihat_Parasara_Hora_Sastra_Vol_1,Brihat_Parasara_Hora_Sastra_Vol_2,Brihat_Samhita,Deva_Keralam_1,Deva_Keralam_2,Gochar_Phaladeepika_Pulippani,Hora_Sara,Jaimini_Sutras,Jataka_Parijata,Jataka_Tatva_Mahadeva,Phaladeepika_English_Translation,Phaladeepika_Mantreswara,Prasna_Marga_Part_1,Saravali,Sarvartha_Chintamani,Uttara_Kalamrita" --graph knowledge-graph/graphify-out/graph.json --apply-to-graph --write

# Live Supabase (one high-impact at a time; review dry output + samples first)
python3 scripts/apply_node_chapter_patch.py --books "Phaladeepika_Mantreswara" --supabase --write

python3 scripts/apply_node_chapter_patch.py --books "Jaimini_Sutras" --supabase --write
```

After writes: re-run `python3 tmp_probe_supabase_patches.py` (or equivalent) and targeted Learn smoke for /learn pages of affected books. Commit updated graph + patch artifacts.

## Safety / Robustness (applied in this session)

- Idempotency preserved (chapter_id + method + confidence); extended to stamp patch_* markers when ch+method+conf already match but patch provenance fields are absent.
- Supabase path: on_conflict upsert of merged properties; prints target count and note that no .bak is written (use Supabase history / prior export for restore).
- would_write / supabase_upsert_targets now reflect actual rows the fast path will attempt (not just "new" applied).
- All live-affecting commands require explicit --write and respect --dry-run.
- Never writes without operator intent.

## Limits

- Patch only lifts nodes whose ids exist in target and for which a patch entry was generated.
- Long-tail nodes per book (e.g. Jaimini ~1600 extra) and misaligned id spaces are out of scope for this patch file + apply script without upstream remapping.
- Quantitative only; no Supabase mutation occurred in this run.
