#!/usr/bin/env python3
"""
Generate embeddings for corpus_chunks and upsert to Supabase.

Usage:
  source portal/.env.local
  python3 scripts/generate-embeddings.py [--limit 100]

Requires: google-genai (text-embedding-004). Set GOOGLE_API_KEY or GEMINI_API_KEY.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "cvce"))

from supabase_corpus_sync import api_request, load_env  # noqa: E402
from knowledge_engine.embeddings import embed_text, get_genai_client  # noqa: E402

FETCH_PAGE = 500
MAX_RETRIES = 3


def fetch_chunks_without_embeddings(env: dict[str, str], limit: int = 0) -> list[dict]:
    """Paginate through corpus_chunks rows missing embeddings."""
    rows: list[dict] = []
    offset = 0
    while True:
        page_size = FETCH_PAGE
        if limit:
            remaining = limit - len(rows)
            if remaining <= 0:
                break
            page_size = min(page_size, remaining)

        path = (
            "/rest/v1/corpus_chunks"
            f"?select=id,source_id,chunk_index,content"
            f"&embedding=is.null"
            f"&order=source_id,chunk_index"
            f"&limit={page_size}&offset={offset}"
        )
        code, body = api_request(env, "GET", path)
        if code != 200:
            raise RuntimeError(f"Failed to fetch chunks (HTTP {code}): {body[:200]!r}")

        batch = json.loads(body)
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    return rows


def patch_embedding(env: dict[str, str], chunk_id: str, vec: list[float]) -> bool:
    payload = {"embedding": vec, "updated_at": datetime.now(timezone.utc).isoformat()}
    for attempt in range(MAX_RETRIES):
        code, body = api_request(
            env,
            "PATCH",
            f"/rest/v1/corpus_chunks?id=eq.{chunk_id}",
            json.dumps(payload).encode(),
            headers={"Prefer": "return=minimal"},
        )
        if code in (200, 204):
            return True
        if code >= 500 and attempt < MAX_RETRIES - 1:
            time.sleep(2 ** attempt)
            continue
        print(f"  failed for {chunk_id}: HTTP {code} {body[:120]!r}", file=sys.stderr)
        return False
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="Max chunks to embed (0 = all)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    env = load_env()
    if not env.get("SUPABASE_URL") or not env.get("SUPABASE_SERVICE_ROLE_KEY"):
        print("error: missing Supabase env (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)", file=sys.stderr)
        return 1

    client = get_genai_client()
    if not client:
        print("error: set GEMINI_API_KEY or GOOGLE_API_KEY for real embeddings", file=sys.stderr)
        return 1
    print("Using Gemini text-embedding-004")

    try:
        chunks = fetch_chunks_without_embeddings(env, limit=args.limit)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not chunks:
        print("No chunks without embeddings — nothing to do.")
        return 0

    print(f"Embedding {len(chunks)} chunks...")

    updated = 0
    skipped = 0
    for ch in chunks:
        content = ch.get("content", "")
        if not content:
            skipped += 1
            continue

        vec = embed_text(client, content)
        if vec is None:
            print(f"  embed failed for {ch['source_id']}#{ch['chunk_index']}", file=sys.stderr)
            skipped += 1
            continue

        if args.dry_run:
            print(f"  would update {ch['source_id']}#{ch['chunk_index']}")
            continue

        if patch_embedding(env, ch["id"], vec):
            updated += 1
            if updated % 20 == 0:
                print(f"  updated {updated}")

    print(f"✓ Embedded/updated {updated} chunks ({skipped} skipped)")

    if updated and not args.dry_run:
        try:
            from knowledge_engine import get_knowledge_engine

            ke = get_knowledge_engine()
            result = ke.on_embeddings_updated(chunk_count=updated)
            print(
                "KnowledgeEngine notified:",
                f"vector_search={result.get('vector_search_available')},",
                f"version={result.get('version')}",
            )
        except Exception as exc:
            print(f"KnowledgeEngine notification skipped: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
