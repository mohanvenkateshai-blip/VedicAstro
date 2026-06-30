# Vedic Knowledge Catalog

**Single source of truth for what texts exist in the Knowledge Graph.**

- **Graph Version:** `newbooks-v1`
- **Nodes:** 26,722
- **Links:** 38,881
- **Total source texts tracked:** 61 (from corpus-manifest.json)
- **Last updated:** 2026-06-29 (deterministic layer)
- **Authority:** This file + `knowledge-graph/graph-version.json` + Supabase `corpus_sources` + `graph_nodes` (newbooks-v1)

---

**🚨 MANDATORY MULTI-AGENT PROTOCOL (ALWAYS APPLY — project law)**  
**At the first indication of any substantial task, immediately launch ≥5 agents in parallel via multiple `Task` tool calls.**  
Include a compliance/reminder/orchestrator agent in the opening wave. Never work sequentially on real work.  
**Source of truth:** `.cursor/rules/multi-agent-mandatory-protocol.mdc` (alwaysApply: true).  
See `docs/MULTI_AGENT_MANDATORY_RULE.md` and `docs/agents-launched.log`. Scale aggressively.

**Execution Model:** Minimum 5 parallel agents + dedicated orchestrator at task start (multiple `Task` calls in first response). See `.cursor/rules/multi-agent-mandatory-protocol.mdc`.

---

## 0. Multi-Agent Health

| Item                      | Requirement / Status               | Notes |
|---------------------------|------------------------------------|-------|
| Minimum Parallel Launch   | 5+ agents via `Task` (first action) | Non-negotiable for any code, data, docs, audit, or analysis work |
| Orchestrator in Wave 1    | Required                           | Scans for single-threaded drift and spawns more agents |
| Rule File Reference       | Must appear in status & handoffs   | `.cursor/rules/multi-agent-mandatory-protocol.mdc` |
| Handoff Snapshots         | Maintainer must include            | Future runs of `scripts/handoff/maintain_context.py` and `AI_TAKEOVER_PACK.md` cite the rule |
| Session Record            | `docs/agents-launched.log`         | Records launches (this session: 6+ agents for handoff propagation) |

**All future generated handoff snapshots are required to reference the multi-agent mandatory protocol rule.**

---

**How to read this:**
- "Core Classical" = the traditional foundational works (mostly from CoreJyothisha PDFs).
- "Additional / Newbooks" = later loose .md files added from Panchang/Gyan/newbooks (12 ingested, 2 skipped as duplicates).
- "Distinct variants" = we intentionally kept separate copies when they are meaningfully different (e.g. two Jaimini treatments, two Ashtakavarga treatments).
- Node counts per text vary because extraction is a mix of deterministic heading/verse parsing + LLM entity extraction. Some texts have rich verse-level nodes; handbooks often have fewer structured nodes but full prose in the vault.

---

## Physical Layout (where the actual knowledge lives)

1. **Raw source markdowns** (the real prose)
   - Stored in Supabase private bucket `corpus-vault`
   - Local working copies historically lived in sibling `Panchang/Gyan/...` (not inside this repo)
   - Never bulk-committed to git (size + copyright reasons)

2. **Extracted Knowledge Graph**
   - Primary: Supabase tables `graph_nodes`, `graph_links`, `corpus_chunks` (with pgvector)
   - Git artifacts (for history + offline):
     - `knowledge-graph/graphify-out/graph.json` (current)
     - `knowledge-graph/graphify-out/graph-core-jyotisha.json`
     - Dated snapshots in `graphify-out/YYYY-MM-DD/`
     - `cvce/graph_rag/graph.json` (runtime copy for CVCE cold starts)

3. **Metadata**
   - `knowledge-graph/graph-version.json` — canonical counts + version label (read this first)
   - `knowledge-graph/corpus-manifest.json` — every raw file we know about (bytes + short sha)
   - `knowledge-graph/ingest-logs/` — narrative history of each ingest wave

4. **Access**
   - **Only** through `KnowledgeEngine` (cvce/knowledge_engine)
   - Portal uses `listCorpusSources()` + `loadBook()` → Supabase (with fuzzy fallbacks for legacy name mismatches)
   - Never direct table queries from app code

**Rule:** If you want to "see" the knowledgebase, query via KE or the portal `/learn` or `/admin/knowledge`. Do not rely on any single committed graph.json as the only truth.

---

## Core Classical Jyotisha (foundational)

These are the traditional works that form the backbone.

(Representative list — full authoritative list is the combination of corpus_sources + graph nodes for newbooks-v1)

- Brihat_Parasara_Hora_Sastra_Vol_1.md
- Brihat_Parasara_Hora_Sastra_Vol_2.md
- Brihat_Jataka.md
- Bhavartha_Ratnakara.md
- Phaladeepika_*
- Jataka_Parijata
- Saravali
- Prasna_Marga_Part_1 / Part_2
- Brihat_Samhita
- Bhrigu_Samhita_TMRao.md
- Deva_Keralam_1/2/3 (Chandra Kala Nadi)
- Laghu_Parashari
- Uttara_Kalamrita
- Jataka_Chandrika
- Graha_Laghava
- Hora_Shastra_Varahamihira
- Vedanga_Jyotisa_Lagadha
- ... (and ~20 total core works)

Many of these went through OCR (marker/deepseek) + multiple LLM passes (deepseek/gemini) because original sources were scanned PDFs.

---

## Additional Texts (Newbooks ingest, 2026-06-29)

12 new .md files promoted into `newbooks-v1`. 2 skipped because they were near-duplicates of existing BPHS volumes.

Ingested:
- Ashtakavarga_System_Comprehensive_Handbook.md (distinct from the patel one)
- Bhava_and_Graha_Balas_BVRaman_1996.md
- Crux_of_Vedic_Astrology_Timing_of_Events1.md
- Introduction_to_Vedic_Astrology_Sanjay_Rath.md
- Vedic_remedies_by_srath_pdf_free.md
- boney_marc_intricate_patterns_of_destiny...
- jaimini_astrology_calculation_of_mandook_dasha...
- patel_cs_aiyar_cas_ashtakavarga.md (distinct Ashtakavarga treatment)
- rath_s_jaimini_maharishis_upadesa_sutra.md (distinct Jaimini treatment)
- the_jyotish_digest_* (several volumes)
- wilhelm_ernst_classical_muhurta_jyotish.md

Skipped (duplicates):
- maharishi_parasaras_brihad...vol_i → already have Brihat_Parasara_Hora_Sastra_Vol_1
- ...vol_ii (same)

Duplicate policy lives in `scripts/ingest-newbooks-md.py` (WORK_DUPLICATES + 92% content similarity).

---

## Special Cases / Multiple Treatments

We deliberately keep some "parallel" texts when they are not the same work:

- Jaimini:
  - Jaimini_Sutras.md (core)
  - rath_s_jaimini_maharishis_upadesa_sutra.md (newbooks)
  - jaimini_astrology_calculation_of_mandook_dasha... (newbooks)

- Ashtakavarga:
  - Ashtakavarga_System_Comprehensive_Handbook.md
  - patel_cs_aiyar_cas_ashtakavarga.md

These appear as separate cards in `/learn`.

---

## Current Problems & Known Mess (being honest)

This catalog exists because the previous state was confusing. Real sources of the "haphazard" feeling:

1. **Name drift between layers**
   - `corpus_sources.canonical_name` (often nice title)
   - `graph_nodes.source_file` (often the filename stem used at extract time)
   - Result: many books showed "0 nodes" until fuzzy `.ilike("%key%")` + multi-candidate lookup was added in `portal/src/lib/books.ts`.

2. **Incremental, multi-tool ingest history**
   - Core 20 via PDF → OCR → LLM batches (deepseek then gemini).
   - Then ad-hoc 14 loose newbooks.
   - Gemini semantic layer was submitted but left in JOB_STATE_RUNNING; we promoted only the deterministic layer.
   - Multiple graph.json copies accumulated.

3. **Sources not inside the repo**
   - You cannot `ls knowledge-graph/raw/` here and see everything. The real files are in the private bucket.
   - Scripts historically referenced absolute paths in a sibling `Panchang/` checkout.

4. **Documentation sprawl**
   - Many handoff snapshots, dated reports, archive/, ingest-logs with overlapping narratives.
   - Old counts (4253, 6437) lingered in some places until aggressively removed.
   - `STATUS.md`, `CONTEXT.md`, `knowledge-engine-status.md` all say similar things with different dates.

5. **Extraction is uneven**
   - Verse-based classics → many small labeled nodes.
   - Modern handbooks → fewer nodes, more "page" or "section" level, plus the full prose fallback.
   - This is why the reader had to do both "nodes view" + "full markdown view" + section parsing.

6. **KnowledgeEngine is new (late June 2026)**
   - Before it, many engines talked directly to GraphRAG or raw JSON.
   - A lot of "wire the KE" cleanup happened in the last days.

---

## How We Access It Now (the organized way)

- **Code path:** `KnowledgeEngine` (see `cvce/knowledge_engine/engine.py`, `integration.py`, `store/supabase_store.py`)
- **Portal library:** `portal/src/lib/books.ts` (loadBook, listBooks) + `corpus.ts`
- **Admin:** `/admin/knowledge` in the portal
- **Learn reader:** `/learn` + `/learn/[bookId]` — now uses parsed markdown headings for real books + graph nodes as enrichment
- **Refresh after new ingest:** `ke.on_new_literature_ingested()` or `POST /knowledge/refresh`

All consumers should go through KE. Direct Supabase or direct file reads are considered technical debt.

---

## Next Improvements (to reduce fear / confusion)

- [ ] Make `corpus_sources` the absolute source of canonical names; during ingest, normalize `graph_nodes.source_file` to match exactly.
- [ ] Populate `corpus_chunks` + embeddings so vector search becomes first-class under KE.
- [ ] One command: `./scripts/ingest-text.sh <file-or-dir>` that does copy → extract → promote → supabase-sync → KE cascade.
- [ ] Expose `ke.list_texts()` or `/knowledge/texts` that returns the catalog with live node counts.
- [ ] Retire or clearly label all the dated graphify-out/ subdirs and old logs.
- [ ] Keep this CATALOG.md as the human entry point; auto-regenerate sections from manifest + Supabase stats.

---

**If you are a new AI or human taking over:** Start here, then:

1. `knowledge-graph/graph-version.json`
2. This file
3. `docs/knowledge-engine-status.md` + `docs/knowledge-engine-architecture.md`
4. `cvce/knowledge_engine/` for the runtime owner
5. `scripts/ingest-*.py` + `supabase-corpus-sync.py` for how data gets in

The Knowledge Graph is real, large, and now has a central owner. The mess you feel is mostly historical build artifacts + naming impedance between layers. We are actively cleaning the surface.

(Generated / curated 2026-06-30 to address exactly this concern.)
