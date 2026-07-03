#!/usr/bin/env python3
"""Re-embed every corpus_chunk with the local bge-small (384-dim) ONNX model,
so the stored document vectors live in the SAME space as the query-time
embedder (knowledge_engine.local_embedder) — the fix that makes production
semantic search actually work.

Prerequisite: the corpus_chunks.embedding column must already be vector(384)
(run the migration SQL first — see MIGRATION.sql printed by --show-migration).
Upserting 384-dim vectors into a vector(768) column will error.

Reads chunk content via Supabase REST, embeds locally in batches (fast, no
API cost, no torch), and PATCHes embeddings back. Idempotent + resumable:
by default only embeds rows where embedding IS NULL, so a re-run after the
migration (which nulls the column) processes everything, and an interrupted
run resumes.

Usage:
  python3 scripts/reembed-corpus-fastembed.py [--limit N] [--batch 256] [--all]
  python3 scripts/reembed-corpus-fastembed.py --show-migration
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "cvce"))

from supabase_corpus_sync import api_request, load_env  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reembed")

MIGRATION_SQL = """\
-- Migrate corpus_chunks embeddings from 768-dim (Gemini/mpnet) to 384-dim
-- (local bge-small). Safe: all existing vectors are being replaced anyway.
-- Run in Supabase dashboard → SQL Editor.

DROP INDEX IF EXISTS idx_corpus_chunks_embedding;
ALTER TABLE corpus_chunks DROP COLUMN IF EXISTS embedding;
ALTER TABLE corpus_chunks ADD COLUMN embedding vector(384);
CREATE INDEX idx_corpus_chunks_embedding
  ON corpus_chunks USING hnsw (embedding vector_cosine_ops);

CREATE OR REPLACE FUNCTION match_corpus_chunks(
  query_embedding vector(384),
  match_count int DEFAULT 8
)
RETURNS TABLE (
  id uuid,
  source_id text,
  content text,
  chunk_index int,
  similarity float
)
LANGUAGE sql STABLE AS $$
  SELECT c.id, c.source_id, c.content, c.chunk_index,
         1 - (c.embedding <=> query_embedding) AS similarity
  FROM corpus_chunks c
  WHERE c.embedding IS NOT NULL
  ORDER BY c.embedding <=> query_embedding
  LIMIT match_count;
$$;
"""


def _iter_missing(env, page: int = 500):
    offset = 0
    while True:
        code, body = api_request(
            env, "GET",
            f"/rest/v1/corpus_chunks?select=id,content&embedding=is.null&order=id&limit={page}&offset={offset}",
        )
        if code != 200:
            logger.error("fetch failed HTTP %s: %s", code, body[:200])
            break
        rows = json.loads(body)
        if not rows:
            break
        yield rows
        offset += len(rows)
        if len(rows) < page:
            break


def _patch(env, chunk_id: str, vec: list[float]) -> bool:
    code, _ = api_request(
        env, "PATCH",
        f"/rest/v1/corpus_chunks?id=eq.{chunk_id}",
        json.dumps({"embedding": vec}).encode(),
        headers={"Content-Type": "application/json", "Prefer": "return=minimal"},
    )
    return code in (200, 204)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="stop after N chunks (0 = all)")
    ap.add_argument("--batch", type=int, default=256, help="embed batch size")
    ap.add_argument("--show-migration", action="store_true", help="print migration SQL and exit")
    args = ap.parse_args()

    if args.show_migration:
        print(MIGRATION_SQL)
        return 0

    env = load_env()
    from knowledge_engine.local_embedder import embed_documents, LOCAL_EMBED_DIM, LOCAL_EMBED_MODEL

    logger.info("Re-embedding with %s (dim=%d)", LOCAL_EMBED_MODEL, LOCAL_EMBED_DIM)
    done = failed = 0
    t0 = time.time()
    batch_ids: list[str] = []
    batch_texts: list[str] = []

    def flush() -> None:
        nonlocal done, failed, batch_ids, batch_texts
        if not batch_ids:
            return
        vecs = embed_documents(batch_texts)
        for cid, vec in zip(batch_ids, vecs):
            if _patch(env, cid, vec):
                done += 1
            else:
                failed += 1
        rate = done / max(time.time() - t0, 1e-6)
        logger.info("  progress: %d done, %d failed (%.0f/s)", done, failed, rate)
        batch_ids, batch_texts = [], []

    for rows in _iter_missing(env):
        for r in rows:
            batch_ids.append(r["id"])
            batch_texts.append(r.get("content") or "")
            if len(batch_ids) >= args.batch:
                flush()
            if args.limit and (done + len(batch_ids)) >= args.limit:
                flush()
                logger.info("Done (limit): %d embedded, %d failed", done, failed)
                return 0 if failed == 0 else 1
    flush()
    logger.info("Done: %d embedded, %d failed in %.0fs", done, failed, time.time() - t0)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
