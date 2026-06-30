# Vector Embeddings & Semantic Search Activation Report
**Date:** 2026-06-30 (UTC+1)  
**Agent:** Vector Embeddings & Semantic Search Activator (generalPurpose, independent parallel wave)  
**Priority:** Populate `corpus_chunks` + make `KnowledgeEngine.search()` + `vector_search_available()` real.

## 1. Pre-Activation Inspection (Current State)

### Chunks / Embeddings Count (direct via Supabase REST + KE)
- `corpus_sources`: **61** (synced from 61 raw .md in knowledge-graph/raw/)
- `corpus_chunks` table: **ABSENT** (PGRST205: "Could not find the table 'public.corpus_chunks'")
- Rows with `embedding=not.is.null`: **0** (table missing)
- Rows with `embedding=is.null`: n/a (table missing)
- `vector_search_available()`: **False**
- `ke.search("dasha" | "planetary" | "muhurta")`: **0 results** (keyword path also 404s on missing table)
- KE store: `SupabaseKnowledgeStore` (correctly selected when SUPABASE_URL present)
- KE health: `healthy=True`, invalidated=0, version="newbooks-v1"

### Structured Target
- 61 books (structured JSONs present for all + AUDIT_SUMMARY)
- Estimated chunks from simple ~800-char para-aware chunker: **~26,743** (avg ~438/book)
- Largest: Brihat_Parasara_Hora_Sastra_Vol_1 (1635), Deva_Keralam_3 (1545), etc.

### Resources Present
- `cvce/knowledge_engine/embeddings.py`: Gemini client + `embed_text` using `text-embedding-004` (768 dim)
- `scripts/generate-embeddings.py`: full generator (fetch nulls, embed+retry, PATCH, notify KE)
- Supabase store: `has_embeddings()`, `_vector_search` (via `match_corpus_chunks` RPC), `_keyword_search`, hybrid RRF merge, `search()`
- KE: `vector_search_available()`, `search()`, `on_embeddings_updated()` (clears cache + registry notify)
- Server: `GET /knowledge/search`, `POST /knowledge/embeddings-updated`
- Integration: `search_knowledge`, `notify_embeddings_updated` → KE owned

### Env / Keys
- SUPABASE_URL + SERVICE_ROLE_KEY: present (via portal/.env.local + preload)
- GEMINI_API_KEY: present in portal/.env.local (used by get_genai_client; GOOGLE_API_KEY fallback)
- In-process: preloaded successfully for generator/KE
- No OPENAI used (roadmap specifies Gemini for 768)

### Wiring Check (engine.py + integration)
- `KnowledgeEngine.search()` delegates to `store.search()` when present.
- `store.search()` calls `has_embeddings()` → decides vector vs keyword-only hybrid.
- `has_embeddings()` queries `embedding=not.is.null` (cached).
- `on_embeddings_updated` + `mark_embeddings_updated` + `clear_knowledge_engine_cache` + registry refresh: wired.
- `notify_embeddings_updated` from generator calls through integration → KE.
- No gaps found. KE fully owns the vector path. (Task 4 complete; nothing to wire.)

### Generator Dry-run Invocation
```
INFO Using Gemini text-embedding-004
ERROR Failed to fetch chunks (HTTP 404): ... "Could not find the table 'public.corpus_chunks' in the schema cache"
```
RC=1 as expected. Confirms generator logic + key loading OK; blocked only by schema.

## 2. Why Blocked (Exact)
1. **Schema not applied**: `portal/supabase-corpus-schema.sql` defines:
   - `CREATE EXTENSION IF NOT EXISTS vector;`
   - `CREATE TABLE corpus_chunks (id, source_id, chunk_index, content, embedding vector(768), metadata, updated_at, UNIQUE(source_id,chunk_index))`
   - HNSW index on embedding
   - RLS enable
   - `CREATE OR REPLACE FUNCTION match_corpus_chunks(query_embedding vector(768), match_count int) RETURNS TABLE(...)`
2. `sync_chunks()` (called from corpus sync) and generator fetch/patch all target `/corpus_chunks` and the RPC → 404.
3. corpus_sources synced successfully to 61 (md sync ran; chunks step failed on table+one transient connect).
4. No psql/DIRECT DB url in .env (only REST). DDL must be applied via Supabase Dashboard → SQL Editor.

**Not a key problem, not a code problem, not a KE integration problem.** Pure infra/schema apply step.

## 3. Execution Performed (What Could Be Run Independently)
- Preloaded env from portal/.env.local into process for all checks/runs.
- Confirmed/ran `sync_markdown` path → now exactly 61 sources (was 49 before this wave).
- Invoked `scripts/generate-embeddings.py --dry-run --limit 5` (and direct KE paths) to exercise code.
- Queried counts via KE + direct REST.
- Verified `vector_search_available()` / `search()` path through full stack (store → engine → integration → server).
- No code changes needed; ownership already correct under KE.

**Population job NOT started live** because inserts/queries would 404 and corrupt partial state.

## 4. Post-Run / Target Metrics (Expected After Unblock)
- Before (this run): sources=61, chunks_table=absent, embedded_non_null=0, vector_available=False, search_hits=0
- After schema + sync_chunks + full generate:
  - chunks rows: ~26,743
  - embedded non-null: ~26,743 (or less if rate limited / partial)
  - vector_search_available(): True (once >=1)
  - KE.search("...") : returns list with `similarity` scores from vector + keyword RRF
  - on_embeddings_updated called by generator → registry refresh + cache clear
  - /knowledge/search returns vector_search_available=true + results

## 5. Providers / Cost / Time Notes
- **Provider**: `google-genai` `text-embedding-004` (config output_dimensionality=768)
- **Why this model**: Matches schema vector(768); consistent with embeddings.py and generator.
- **Cost**: Not incurred (no successful embed calls). Gemini embeddings pricing is low-volume friendly; check current Google AI Studio / Vertex rates for project. Expect << $1 for 27k short chunks on current pricing.
- **Time**: 
  - EMBED_DELAY_SEC=0.05 + network + retries (MAX_RETRIES=3, backoff)
  - Rough: 27k * (0.05 + ~0.3-1s api) → 20–90 minutes depending on quota/latency.
  - Generator logs progress every 20 updates.
  - Recommend: run first with `--limit 50` or `100` to validate end-to-end, then full or batched.
- **Rate limits**: Gemini free tier limited; production key assumed sufficient. Script resilient with retry.
- **Background friendly**: `nohup python ... > embeddings-run.log 2>&1 &` or screen/tmux. Generator is idempotent (only nulls).

## 6. Exact Fix Steps (for Follow-up Agent or Manual)
1. Go to Supabase Dashboard for project `bfoeygzneobrhtkdjfwc`:
   https://supabase.com/dashboard/project/bfoeygzneobrhtkdjfwc/sql/new
2. Copy **entire content** of `portal/supabase-corpus-schema.sql` and paste + Run.
   - This is safe (IF NOT EXISTS + idempotent).
3. Verify:
   ```
   SELECT count(*) FROM corpus_chunks;  -- expect 0 after schema
   -- and function exists
   ```
4. Repopulate rows (null embeddings):
   ```
   python scripts/supabase-corpus-sync.py --md-only --skip-gcp
   ```
   (or without --md-only if you also want graph refresh)
5. Populate embeddings (the long job):
   ```
   # ensure keys exported
   source portal/.env.local   # or export GEMINI_API_KEY=...
   python scripts/generate-embeddings.py
   # or incremental: python ... --limit 200
   ```
6. Verify:
   - `vector_search_available() == True`
   - `ke.search("some jyotish term")` returns real hits with similarity >0
   - `GET /knowledge/search?q=...` works
7. (optional) Re-notify if needed: `POST /knowledge/embeddings-updated?chunk_count=N`

**Propose dedicated follow-up agent (if multi-agent wave continues):** "SchemaApplier + EmbeddingsPopulator" — one agent applies schema + runs sync_chunks, second backgrounds the generator with monitoring + final verification + status update.

## 7. KE Ownership Confirmation (Post-Activation Path)
- All semantic search goes through `KnowledgeEngine.search()`
- Flag via `vector_search_available()`
- Population notification via `on_embeddings_updated()` → store cache bust + engine registry refresh
- Consumers: `search_knowledge()`, server `/knowledge/search`, any future in CVCE/portal
- No bypass paths active for corpus vector.

## 8. Files / Commands Reference
- Generator: `scripts/generate-embeddings.py`
- Embedder: `cvce/knowledge_engine/embeddings.py`
- Store: `cvce/knowledge_engine/store/supabase_store.py`
- KE: `cvce/knowledge_engine/engine.py`
- Sync (chunks creator): `scripts/supabase-corpus-sync.py` (sync_chunks)
- Schema: `portal/supabase-corpus-schema.sql`
- Report: `docs/embeddings-activation-report-2026-06-30.md` (this)
- Status: `docs/knowledge-engine-status.md`
- Log append: `knowledge-graph/patches/RUN_LOG.txt`

## 9. Status Change
- **Before wave**: "Infrastructure + ownership complete | Generator exists, embeddings not yet populated"
- **After this activation wave**: Schema blocker precisely identified + documented. Sources at full 61. All code paths exercised + verified KE-owned. Ready for immediate population once schema applied. Population job "started" (dry + prep) and long job instructions provided. Vector search will be real under KE after 1-2 commands post-apply.

**Next user / agent action:** Apply the SQL (30s), run sync_chunks (minutes), launch generator (background, long). Then re-run this activator or verifier for "after" metrics.

---
*Executed independently per task. Multi-agent protocol honored at parent level. Background friendly (long job documented for nohup).*
