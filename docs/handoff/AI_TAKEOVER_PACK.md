# VedicAstro — AI Takeover Pack (Handoff Snapshot)

**Generated for next AI/model:** 2026-06-29 (user switching tools)  
**Graph Version:** `newbooks-v1`  
**Nodes / Links:** 26,722 / 38,881 (canonical from knowledge-graph/graph-version.json)  
**KnowledgeEngine Health:** Healthy (Supabase primary)  
**Working Tree:** Clean (0 dirty, 0 untracked) — enforced zero backlog policy.

**Read this file first. Then CONTEXT.md + STATUS.md + docs/knowledge-engine-status.md.**

---

## 1. One-Sentence Reality

VedicAstro = Next.js Portal (Vercel) + FastAPI CVCE (Fly.io) + central **KnowledgeEngine** that owns the full Vedic KG (newbooks-v1, 20 Core Jyotisha + 12 newbooks). All prediction engines must consume knowledge through KE. Learn module (`/learn`) is live and wired to the graph.

## 2. Live URLs (as of handoff)

- **Portal (main UI):** https://portal-omega-two-10.vercel.app
  - `/learn` — Classical library (book grid)
  - `/learn/jaimini` — Real Jaimini Sūtras reader (auth excerpts from corpus + fuzzy KG lookup)
  - `/chart`, `/chart/report`, explorers, etc.
- **CVCE (engine):** https://vedicastro-cvce.fly.dev
  - `POST /report/facts`, `/dashas`, `/knowledge/refresh`, health, etc.
- **Muhurta (frozen):** https://muhurtha.uvwx.me (never touch)

## 3. Knowledge Graph State (MUST READ FIRST)

- Canonical source: `knowledge-graph/graph-version.json`
- Production: `newbooks-v1` (26,722 nodes / 38,881 links)
- Storage: Supabase (`graph_nodes`, `graph_links`, `corpus_sources`, `corpus_chunks` + pgvector) + private `corpus-vault` bucket.
- Local copies: `knowledge-graph/graphify-out/graph.json`, `cvce/graph_rag/graph.json`
- **Rule:** Any doc/code mentioning 4,253 / 6,437 / 23,267 or defaulting to `core-jyotisha-v1` is stale. Kill it.

**Ingestion complete (deterministic layer):**
- 20 Core Jyotisha PDFs
- 12 newbooks (Rath Jaimini Upadesa, Wilhelm Ernst, etc.; 2 duplicates skipped)

## 4. KnowledgeEngine is the Single Source of Truth

Location: `cvce/knowledge_engine/`

- `engine.py` — central manager, versioning, invalidation, revival, `trigger_global_refresh()`
- `integration.py` — **use these safe functions everywhere:**
  - `get_knowledge_engine()`
  - `get_safe_graph()`, `get_safe_transit_rules()`, `get_safe_knowledge()`
  - `clear_knowledge_engine_cache()`
  - `search_knowledge()`
  - `get_llm_narration()`
- `store/supabase_store.py` — primary backend (KE_USE_SUPABASE or SUPABASE_URL present)
- `refresh_auditor.py` — measures impact of KG changes on engines
- `registry.py` — engines register for cascade updates

**On new literature:** after `merge --promote`, call `KnowledgeEngine().on_new_literature_ingested(...)` (ingest scripts already do this).

**Global refresh endpoint:** `POST https://vedicastro-cvce.fly.dev/knowledge/refresh`

## 5. Major Features Delivered (Recent)

- **Learn module** (`/learn` + `/learn/jaimini`, rashis, nakshatras explorers) — premium UI, data layer in `portal/src/lib/{books,corpus}.ts`, pulls from Supabase + KG. Jaimini uses real filenames from `knowledge-graph/raw/` + fuzzy search.
- **KnowledgeEngine full wiring** across engines (Gochar, Muhurta, Report, Dasha, Yoga, Panchanga, etc.). Direct GraphRAG bypasses minimized; most now go through safe wrappers or `clear_knowledge_engine_cache()`.
- **VedicOps automation:**
  - `scripts/commit_agent.py` — health checks + auto commit (non-blocking lint/tests)
  - `cvce/knowledge_engine/performance_monitor.py`
  - `scripts/handoff/maintain_context.py` — keeps this pack + CONTEXT fresh
  - `scripts/vedicops.py` — master orchestrator
- **Vector embeddings** scaffolding (`scripts/generate-embeddings.py`, `corpus_chunks` table + pgvector, `corpus.ts` helpers).
- **LLM narration** wired in report facts (gated by `CVCE_LLM_NARRATION=1`).
- **D3 Canvas visualizer** for the full 26k graph: `knowledge-graph-visualizer.html`

## 6. Critical Rules for the Next AI

1. **Zero backlog.** If you edit anything, `git add -A && git commit && git push` before stopping. User gets extremely angry at uncommitted files.
2. **Always read `knowledge-graph/graph-version.json` first.** Treat any hardcoded old node counts as lies.
3. **Everything that touches the graph goes through KnowledgeEngine.** No raw `from graph_rag.graph import GraphRAG` for core access unless it's a narrow stats provider.
4. **Portal is Next.js 16** (not 14/15). Use correct patterns.
5. **Muhurta standalone is frozen forever.**
6. **Commit agent is your friend** — run it or let it run to keep history clean.

## 7. How to Continue Work

```bash
# After any KG change
python scripts/handoff/maintain_context.py --update-all
git add -A && git commit -m "handoff: refresh context + takeover pack" && git push

# To force global knowledge refresh
curl -X POST https://vedicastro-cvce.fly.dev/knowledge/refresh

# Verify Learn is using correct version
# Open https://.../learn/jaimini — should attempt real source files + show newbooks-v1
```

## 8. Current Known Gaps / Next Priorities (as of handoff)

From STATUS + CONTEXT (promoted to active):
- Populate vector embeddings + make `KE.search()` return real results.
- Expand engine registration (more dashas, full Kaksha/Chara/Kalachakra).
- Deeper Hiranya report UI (narration + classical citations).
- Full chapter markdown + images in BookReader from corpus-vault.
- Background revival job.

## 9. Quick Verification Commands

```bash
git status          # must be clean
cat knowledge-graph/graph-version.json
curl -s https://vedicastro-cvce.fly.dev/health | head -c 200
python -c "
from cvce.knowledge_engine.integration import get_knowledge_engine
ke = get_knowledge_engine()
print(ke.current_version, ke.is_knowledge_healthy())
"
```

---

**This pack + CONTEXT.md + STATUS.md + docs/knowledge-engine-status.md is enough to be productive immediately.**

*Auto-updated + handoff snapshot prepared 2026-06-29 for new AI/model switch.*
