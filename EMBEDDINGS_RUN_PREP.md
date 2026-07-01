# EMBEDDINGS_RUN_PREP.md

**Date:** 2026-06-30  
**Status:** PAUSED — Gemini quota exhausted (per CONTEXT.md). Stop all paid calls.  
**Purpose:** Quantitative prep and exact command sequence for first embeddings activation run (post schema+sync).  
**Constraints:** Do not touch Supabase, do not run the real generator yet, do not edit chunking strategy. Minimal changes.  
**Resume note:** Resume embeddings when Gemini quota resets (monitor quota dashboard; re-enable via run-embeddings.sh). No paid calls until then.

---

## 1. Expected totals (exact, locally replicated)

Chunking logic replicated verbatim from `scripts/supabase-corpus-sync.py:sync_chunks` (no edits):

```python
paras = _re.split(r"\n\s*\n", text)
chunks, buf = [], ""
for p in paras:
    if len(buf) + len(p) > 800 and buf:
        chunks.append(buf.strip())
        buf = p
    else:
        buf = (buf + "\n\n" + p).strip()
if buf:
    chunks.append(buf)
```

Files considered: only `knowledge-graph/raw/*.md` with `len(data) >= 500`.

**Results:**
- Books processed: **61**
- **Total chunks: 26,743** (exact match to prior estimate of ~26,743; delta = 0)
- Avg per book: 438.4
- Median: 268
- Range: min 4, max 1,635

**Top 5 largest by chunk count:**
1. `Brihat_Parasara_Hora_Sastra_Vol_1`: 1,635 chunks
2. `Deva_Keralam_3`: 1,545 chunks
3. `Deva_Keralam_2`: 1,310 chunks
4. `Brihat_Samhita`: 1,203 chunks
5. `Phaladeepika_English_Translation`: 1,090 chunks

All other books produce fewer chunks (down to single-digit for short references/handbooks). Full per-book counts available via the replication script in session history.

---

## 2. Generator observations (narrow slices only)

Read targets (no broad dumps):
- `scripts/generate-embeddings.py`
- `cvce/knowledge_engine/embeddings.py`

**Positive / correct:**
- Resumable by design: `fetch_chunks_without_embeddings` queries `embedding=is.null` only. Safe to interrupt/re-run.
- Progress: `logger.info("updated %d chunks", updated)` every 20 successes + final `(updated, skipped, failed)`.
- `--limit N` and `--dry-run` are wired in `argparse` and respected in fetch + loop.
- `notify_knowledge_engine(updated)` called at end (if `updated>0` and not dry-run) → local KE + optional CVCE POST.
- PATCH writes `embedding` + `updated_at`; pre-existing `source_id`/`chunk_index`/`content`/`metadata` from sync are untouched.
- `embed_text` uses `text-embedding-004` + `output_dimensionality=768` (matches schema `vector(768)`).
- Content safety cap inside embed: `text[:8000]`.

**Obvious items to be aware of (no code changes here):**
- Key loading split: `load_env()` only pulls Supabase/GCP keys. `get_genai_client()` reads `os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")` directly. **Runner must source the full `portal/.env.local`.**
- Retry is generic: `embed_with_retry` and patch loops use `2**attempt` backoff on `None`/5xx. No 429/response-header backoff or quota introspection.
- Per-chunk delay is small (`EMBED_DELAY_SEC = 0.05`); wall time dominated by network + model latency.
- No batch embedding calls; one request per chunk.
- If table missing (pre-schema), fetch will 404 — expected and clean failure.
- Logging uses `logging.basicConfig(INFO)`; when tee'd it is readable.
- `sys.path` inserts for `scripts/` and `cvce/` assume invocation from repo root or `python3 scripts/generate-embeddings.py`.

No functional blockers found for a controlled first run now that credits exist. Resume + limit make it safe.

---

## 3. Convenience runner

Created: `scripts/run-embeddings.sh` (executable).

Features:
- Sources `portal/.env.local` with `set -a` (exports GEMINI + Supabase keys).
- Forwards all args to the generator (e.g. `--limit 50`, `--dry-run`).
- Unbuffered python (`-u`) + `tee -a embeddings-run.log` at repo root.
- Desktop notify at end (prefers `terminal-notifier`, falls back to `osascript`).
- Prints exact verification one-liners at end of each run.
- Idempotent-friendly: safe to run repeatedly; generator only processes nulls.

Make / permissions already applied via prep.

---

## 4. Recommended first commands (post schema + sync_chunks)

**After** `portal/supabase-corpus-schema.sql` has been applied and `sync_chunks` has populated `corpus_chunks` with `embedding=NULL`:

### 4.1 Small test batch (FIRST real action)

```bash
# Preferred (runner handles env + log + notify + prints follow-ups):
./scripts/run-embeddings.sh --limit 50
```

Direct equivalent:
```bash
source portal/.env.local
python3 -u scripts/generate-embeddings.py --limit 50 2>&1 | tee -a embeddings-run.log
```

Inspect `embeddings-run.log` for:
- "Using Gemini text-embedding-004"
- "Embedding 50 chunks..."
- "updated 20 chunks", "updated 40 chunks"
- Final: "Done: embedded/updated 50 chunks (0 skipped, 0 failed)"
- notify output lines

### 4.2 Verify the test batch

```bash
# Should report very few (or zero) in the first pages if the batch covered the head:
python3 scripts/generate-embeddings.py --dry-run --limit 5
```

Local KE probe:
```bash
source portal/.env.local
python3 -c '
import os, sys
sys.path.insert(0, "cvce")
from knowledge_engine.engine import KnowledgeEngine
ke = KnowledgeEngine()
print("vector_search_available:", ke.vector_search_available())
hits = ke.search("dasha", top_k=3)
print("search_hits:", len(hits))
for h in hits[:2]:
    print(" ", h.get("source_id"), "sim=", h.get("similarity"))
'
```

Expect `vector_search_available: True` and `similarity` floats once any embeddings exist.

### 4.3 Continue (examples)

```bash
# Next safe slice:
./scripts/run-embeddings.sh --limit 500

# Or finish everything remaining:
./scripts/run-embeddings.sh
```

Re-running the same command is always safe.

---

## 5. Background how-to

```bash
# Fire-and-forget; runner appends to embeddings-run.log and notifies at end:
nohup ./scripts/run-embeddings.sh > /dev/null 2>&1 &

# Watch progress live:
tail -f embeddings-run.log

# If you want the runner's stdout also captured in nohup (redundant but explicit):
nohup ./scripts/run-embeddings.sh >> embeddings-run.log 2>&1 </dev/null &
```

The script itself timestamps start/end and records the args used.

---

## 6. Verification one-liners (exact, copy/paste)

Printed by the runner at end of every invocation. Also listed here for reference:

```bash
# 1) Remaining nulls check (expect "nothing to do" when complete):
python3 scripts/generate-embeddings.py --dry-run --limit 5

# 2) Local engine vector + search:
source portal/.env.local
python3 -c '
import os, sys
sys.path.insert(0, "cvce")
from knowledge_engine.engine import KnowledgeEngine
ke = KnowledgeEngine()
print("vector_search_available:", ke.vector_search_available())
hits = ke.search("dasha", top_k=3)
print("search_hits:", len(hits))
for h in hits[:2]:
    print(" -", h.get("source_id"), "sim~", round(h.get("similarity", 0), 4) if h.get("similarity") is not None else None)
'

# 3) If a local CVCE server is up (optional):
# curl -sS "http://localhost:8000/knowledge/health" | python3 -m json.tool || true
# curl -sS "http://localhost:8000/knowledge/search?q=muhurta&top_k=3" | python3 -m json.tool || true

# 4) Production smoke (only after a portal deploy that touches Learn/KE paths):
# ./scripts/smoke-learn-production.sh
```

Additional quantitative checks (manual):
- Supabase Dashboard → Table Editor → `corpus_chunks`: count rows with `embedding IS NOT NULL` should rise toward 26,743.
- `corpus_sources` remains 61.

---

## 7. Rough time / cost note

- Model: `google-genai` + `text-embedding-004` (768 dim, matches schema).
- Throughput variables: `EMBED_DELAY_SEC=0.05` + network + model latency + up to 2 retries on transient errors.
- Rough full-run wall time: **20–90 minutes** for ~26.7k chunks (varies with quota headroom and latency).
- Cost: Gemini embeddings are low-volume friendly. Prior estimate for this corpus: **<< $1** on current pricing. Verify your project's Google AI Studio / Vertex rates.
- Rate limits: Free-tier keys can 429/throttle on a full run; a project key with quota is recommended for one-shot. The script resumes cleanly.
- Batching strategy for humans: `--limit 50` (first), `--limit 500`, then full, or just full if you trust the key.

---

## 8. Minimal sequence summary (post schema+sync)

1. Schema applied + `sync_chunks` done → 26,743 rows with `embedding=NULL`.
2. **First real action**: `./scripts/run-embeddings.sh --limit 50`
3. Inspect log + run dry-run check + local KE probe.
4. Iterate with larger `--limit` or full run as desired.
5. Final dry-run + KE probe + (optional) production smoke.
6. Commit/push only if portal-visible behavior changed (per token discipline).

---

## 9. Artifacts from this prep

- `scripts/run-embeddings.sh` — new executable convenience wrapper.
- `EMBEDDINGS_RUN_PREP.md` — this file (counts + commands).
- No edits to chunking, generator, or Supabase-touching scripts.

All numbers above were produced by local replication against the current `knowledge-graph/raw/` tree (61 qualifying .md files) using the exact paragraph-aware ~800 char logic.

---

**Do not run the generator or touch Supabase from this prep turn.** Use the commands above when ready for the controlled activation wave.
