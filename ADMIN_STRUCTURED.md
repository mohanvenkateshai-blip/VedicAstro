# ADMIN_STRUCTURED — Structured Library Ops (CLI)

Priority #5 KnowledgeEngine surface exposed for safe, repeatable operations and CI.

## Commands (via vedicops)

All commands default to **dry-run** (preview, no mutation) + structured logging.

```bash
# Show current structured coverage (read-only, always safe)
python scripts/vedicops.py structured show-coverage

# Preview rebuild of chapter JSONs for all books (or specific)
python scripts/vedicops.py structured rebuild-structured --all --dry-run
python scripts/vedicops.py structured rebuild-structured "Brihat_Samhita,Ashtakavarga_System_Comprehensive_Handbook" --dry-run

# Actually execute the rebuild (mutates knowledge-graph/structured/*.json)
python scripts/vedicops.py structured rebuild-structured --all --force

# Preview remap of KE nodes → chapters
python scripts/vedicops.py structured remap-book --dry-run
python scripts/vedicops.py structured remap-book "Brihat_Samhita" --dry-run

# Remap with Supabase node source (if SUPABASE_* present)
python scripts/vedicops.py structured remap-book --supabase --force

# Invalidate all nodes mapped to a chapter (use with care)
python scripts/vedicops.py structured invalidate-chapter "Brihat_Samhita" "ch-1" --dry-run
python scripts/vedicops.py structured invalidate-chapter "Brihat_Samhita" "ch-1" --force --reason manual
```

## What Each Command Does

| Command                | Effect (dry)                          | Effect (--force)                                      | Writes To                              |
|------------------------|---------------------------------------|-------------------------------------------------------|----------------------------------------|
| show-coverage          | Prints book/chapter/patch stats       | Same (read-only)                                      | —                                      |
| rebuild-structured     | Shows current counts + note           | Runs scripts/build_structured_library.py              | knowledge-graph/structured/*.json      |
| remap-book             | Shows patch stats + target            | Runs scripts/map_nodes_to_structured.py               | knowledge-graph/patches/node-chapter-map.json |
| invalidate-chapter     | Resolves nodes for chapter, shows IDs | Calls KE invalidate() on those nodes (in-memory)      | KE process invalidation set (transient unless persisted elsewhere) |

## Safety Notes

- **Default is dry-run.** You must pass `--force` to mutate.
- `invalidate-chapter` blocks nodes from being returned by safe getters for the life of the KnowledgeEngine instance (or until `revalidate`). Use for bad chapters; remember to re-ingest or remap to restore.
- Rebuild + Remap are the "source of truth" steps for the Learn reader and node→chapter provenance. Run them after editing raw sources or when mappings drift.
- Supabase path for remap requires `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` (or `portal/.env.local`). Without them it falls back to file graph.
- These commands are intentionally thin wrappers over the canonical scripts (`build_structured_library.py`, `map_nodes_to_structured.py`) and KE methods (`rebuild_structured_library`, `remap_nodes_to_structured`, `invalidate`, `get_nodes_for_chapter`).
- KE must be importable (repo root on `sys.path`). `vedicops.py` now bootstraps `parents[1]` correctly.

## Recommended Sequences

After new raw literature lands or manual edits to a book's markdown:

```bash
python scripts/vedicops.py structured rebuild-structured "Your_Book_Title" --force
python scripts/vedicops.py structured remap-book "Your_Book_Title" --force
python scripts/vedicops.py structured show-coverage
```

After detecting a bad chapter (e.g., OCR garbage or superseded content):

```bash
python scripts/vedicops.py structured invalidate-chapter "Your_Book_Title" "ch-07" --force --reason error_in_source
# Later, when fixed:
python scripts/vedicops.py structured remap-book "Your_Book_Title" --force
```

## Programmatic Use (from Python)

```python
from cvce.knowledge_engine.integration import (
    get_structured_coverage,
    rebuild_structured_library,
    remap_nodes_to_structured,
    rebuild_and_remap_structured,
    invalidate_chapter,
)

print(get_structured_coverage()["books"])

# Dry-run friendly wrappers exist; callers control mutation
res = rebuild_structured_library(books=["Brihat_Samhita"])
print(res)

inv = invalidate_chapter("Brihat_Samhita", "ch-1", reason="manual")
print(inv)
```

## Exit / Output

- Human runs: readable blocks + one-line `OK ...` summaries.
- Scripts/CI: parse the returned dict/JSON or grep the `OK` line.
- All paths log via `logging` at INFO when not `--quiet`.

## Health / Verification

```bash
python scripts/vedicops.py structured show-coverage
python -B scripts/vedicops.py structured rebuild-structured --dry-run
python -B scripts/vedicops.py structured remap-book --dry-run
python -B scripts/vedicops.py structured invalidate-chapter "Brihat_Samhita" "ch-1"
```

See also:
- `scripts/verify_structured_books.py` (deeper per-book checks + KE smoke)
- `cvce/knowledge_engine/integration.py` (safe wrappers)
- `cvce/knowledge_engine/engine.py` (core rebuild/remap/invalidate impl)
