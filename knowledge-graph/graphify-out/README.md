# graphify-out/

This is the working / history area for Knowledge Graph extraction outputs.

**Current production files (the ones that matter):**
- `graph.json` — the promoted newbooks-v1 graph
- `graph-core-jyotisha.json` — the core 20 classical before newbooks merge

Everything else (dated folders like `2026-06-27/`, `batch/`, `cache/`, `graph-*.json` from individual model runs, `.bak` files) is historical build output from the multi-pass ingest (OCR + DeepSeek + Gemini + Grok experiments).

Do not treat any of these as the single source of truth at runtime. 

The authoritative live data is in Supabase under graph version `newbooks-v1`.

See parent `../README.md` and `../KNOWLEDGE_CATALOG.md`.

(Added 2026-06-30 to stop people from getting lost here)
