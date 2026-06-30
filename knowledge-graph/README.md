# Knowledge Graph Directory

This folder contains **build artifacts, manifests, and history** for the Vedic Knowledge Graph.

**Do not panic** when you see many files and dated folders. This is normal for an incremental multi-month ingest involving OCR + several LLMs.

## Start Here

- `KNOWLEDGE_CATALOG.md` — The human explanation of what texts we have (61 sources), why it looks messy, and how everything is actually accessed today.
- `graph-version.json` — The single source of truth for the current production counts and version label (`newbooks-v1`).

## What the Subfolders Mean

- `raw/` — (not present in this checkout) The original .md sources live in Supabase `corpus-vault` bucket. We do not commit the full prose here.
- `graphify-out/` — All the intermediate and final graph JSONs from different extractors (deepseek, gemini, grok, deterministic, etc.) and dated runs. 
  - `graph.json` (and `graph-core-jyotisha.json`) are the promoted ones.
  - Dated subfolders and `batch/`, `cache/` are historical. Safe to ignore for day-to-day work.
- `ingest-logs/` — Narrative records of each big ingest wave (Core Jyotisha, Newbooks, etc.). Useful for archaeology, not for current state.
- `digests/` — LLM-generated short summaries of certain texts (auxiliary).
- `chunks/` — Internal chunking artifacts from one of the graphify passes.

## Current Truth

The live, queryable knowledge is in **Supabase**:
- Tables: `corpus_sources`, `graph_nodes`, `graph_links`, `corpus_chunks`
- Bucket: `corpus-vault`

All application code must go through the `KnowledgeEngine` (see `cvce/knowledge_engine/`).

## If you are auditing or taking over

1. Read `KNOWLEDGE_CATALOG.md`
2. Check `graph-version.json`
3. Use the portal `/learn` or `/admin/knowledge` to browse what is actually loaded
4. To force a refresh after changes: `POST /knowledge/refresh` on CVCE or call `ke.trigger_global_refresh()`

The apparent chaos is mostly the visible history of how we got 26k+ nodes from PDFs and loose files. The runtime system is now centralized.

(2026-06-30 — added to reduce fear when people ls this directory)
