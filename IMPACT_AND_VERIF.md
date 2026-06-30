# IMPACT_AND_VERIF — Embeddings + Patches Activation

**Scope:** Discovery of call sites + provenance consumers + minimal verification additions (no broad refactors).

## When embeddings land: these 4 things light up immediately

1. `KnowledgeEngine.search()` / `search_knowledge()` (via integration) + `GET /knowledge/search`
   - Returns real hybrid results: `{source_id, content, chunk_index, similarity?, ...}`
   - `vector_search_available()` flips to `True`
   - Endpoint already wires through KE; portal proxy already allows `knowledge/*`

2. Classical passage retrieval in prediction paths
   - Currently search_knowledge has almost no production callers (only tests + server).
   - Once live, dasha/yoga/ashtakavarga/report can add cheap "supporting passages" pulls using terms like "vimshottari", "muhurta", specific yogas. Results carry source_id ready for chapter mapping.

3. Chapter/hierarchy provenance already wired in several places (lights up richer citations)
   - **Consumed today (via get_structured_book + get_* + patch):**
     - `cvce/vedic_engine/prediction/dasha.py`: `_resolve_dasha_citation`, sets `result.chapter_citation`, `hierarchy_path`
     - `cvce/vedic_engine/prediction/ashtakavarga.py`: `_resolve_akv_citation`, sets on akv
     - `cvce/vedic_engine/prediction/yoga.py`: `_resolve_chapter_citation`, sets on y
     - `cvce/app/report_facts.py`: warmup calls, `get_hierarchy_for_node` on graph_matches/yoga_citations, surfaces `classical_sources.{yoga,dasha,ashtakavarga}_chapter_citation`
   - **Portal Learn (fully using patch provenance today):**
     - `portal/src/lib/books.ts`: `loadNodeChapterPatch`, `buildNodeProvenanceMap`, `enrichChaptersWithNodeIds`
     - `portal/src/app/(main)/learn/[bookId]/page.tsx` + `BookReaderClient.tsx`: attachProvenance, nodeProvenance, "Sourced from" UI, chapterNodesMap
   - **Imported but minimal use (warmup only):** muhurta_yogas, gochar, panchanga, some synthesis.

4. Verification + admin exploration paths
   - New `scripts/verify_knowledge_embeddings.py`
   - Guarded `test_real_ke_search_when_live` in `cvce/tests/test_knowledge_search.py`
   - Admin `KnowledgeExplorer` + future book "related passages" can surface `/knowledge/search` hits (source_id → chapter via existing patch logic)

## Recommended first verification commands after population

```bash
# 1) Structured (already) + embeddings together
python3 scripts/verify_structured_books.py --ke-smoke

# 2) New embeddings-specific verifier (prefers integration wrapper)
python3 scripts/verify_knowledge_embeddings.py

# With explicit real gate (for the pytest addition)
REAL_KE_SEARCH=1 python -m pytest cvce/tests/test_knowledge_search.py::test_real_ke_search_when_live -q -s

# 3) Direct smoke via running CVCE (or local)
curl -sS "http://localhost:8000/knowledge/search?q=dasha&top_k=3" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("vector_search_available"), len(d.get("results",[])), [r.get("source_id") for r in d.get("results",[])[:2]])'

# 4) Portal Learn structured smoke (unchanged requirement)
./scripts/smoke-learn-production.sh https://your-portal.vercel.app
```

Also useful:
- `python3 scripts/generate-embeddings.py --notify` (or equivalent) then the above
- After notify, `ke.on_embeddings_updated()` / `POST /knowledge/embeddings-updated`

## Small safe wiring / test additions made

- Created `scripts/verify_knowledge_embeddings.py` (standalone, real-path, prints counts + PASS/FAIL, checks vector + 4 searches for source_id/similarity, optional hierarchy sample).
- Extended `cvce/tests/test_knowledge_search.py` with:
  - `import os`
  - guarded `test_real_ke_search_when_live()` (skipped unless `REAL_KE_SEARCH=1`)
- No other code changes. All discovery used narrow grep + limited reads.

## Notes / gaps observed (for later)

- `search_knowledge` is exported and ready but has very few live callers outside tests/server. First high-leverage use: inside prediction enhancers or a "classical support" block in reports.
- Search results today give `source_id` (chunk provenance); joining to chapter provenance requires the source_id to map into the node-chapter patch world (or chunks to carry chapter metadata at ingest time). The optional provenance check in verifier is soft.
- Admin corpus search (KnowledgeExplorer) uses graph node search, not yet the KE corpus chunk semantic path.

## Links

- Structured Learn smoke: `scripts/smoke-learn-production.sh`
- Structured books verifier (includes KE smoke): `scripts/verify_structured_books.py`
- Embeddings activation context: `docs/embeddings-activation-report-2026-06-30.md`
- KE status: `docs/knowledge-engine-status.md`
- Patch provenance: `knowledge-graph/patches/node-chapter-map.json` + per-book `patch-*.json`
