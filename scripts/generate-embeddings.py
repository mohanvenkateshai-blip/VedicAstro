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
import logging
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "cvce"))

from supabase_corpus_sync import api_request, load_env  # noqa: E402

from knowledge_engine.embeddings import embed_text, get_genai_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FETCH_PAGE = 500
MAX_RETRIES = 3
EMBED_DELAY_SEC = 0.05


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
    payload = {"embedding": vec, "updated_at": datetime.now(UTC).isoformat()}
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
            time.sleep(2**attempt)
            continue
        logger.error("patch failed for %s: HTTP %s %s", chunk_id, code, body[:120]!r)
        return False
    return False


def embed_with_retry(client, text: str, retries: int = MAX_RETRIES) -> list[float] | None:
    for attempt in range(retries):
        vec = embed_text(client, text)
        if vec is not None:
            return vec
        if attempt < retries - 1:
            time.sleep(2**attempt)
    return None


def notify_knowledge_engine(chunk_count: int) -> dict | None:
    """Notify local KnowledgeEngine and optionally a running CVCE server."""
    result: dict | None = None

    try:
        from knowledge_engine.integration import notify_embeddings_updated

        result = notify_embeddings_updated(chunk_count=chunk_count)
        logger.info(
            "KnowledgeEngine notified: vector_search=%s version=%s",
            result.get("vector_search_available"),
            result.get("version"),
        )
    except Exception as exc:
        logger.warning("KnowledgeEngine local notification skipped: %s", exc)

    base = (os.environ.get("CVCE_BASE_URL") or os.environ.get("CVCE_URL") or "").strip()
    if base:
        url = base.rstrip("/") + "/knowledge/embeddings-updated"
        try:
            proc = subprocess.run(
                [
                    "curl",
                    "-sS",
                    "-X",
                    "POST",
                    f"{url}?chunk_count={chunk_count}",
                    "-w",
                    "\n%{http_code}",
                ],
                capture_output=True,
                timeout=30,
            )
            if proc.returncode == 0 and b"\n" in proc.stdout:
                *body_lines, code_line = proc.stdout.rsplit(b"\n", 1)
                code = int(code_line.decode().strip())
                if code < 400:
                    logger.info("CVCE server notified at %s (HTTP %s)", url, code)
                else:
                    logger.warning(
                        "CVCE notify failed HTTP %s: %s",
                        code,
                        b"\n".join(body_lines)[:200].decode(errors="replace"),
                    )
        except Exception as exc:
            logger.warning("CVCE server notification skipped: %s", exc)

    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="Max chunks to embed (0 = all)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    env = load_env()
    if not env.get("SUPABASE_URL") or not env.get("SUPABASE_SERVICE_ROLE_KEY"):
        logger.error("missing Supabase env (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)")
        return 1

    client = get_genai_client()
    if not client:
        logger.error("set GEMINI_API_KEY or GOOGLE_API_KEY for real embeddings")
        return 1
    logger.info("Using Gemini text-embedding-004")

    try:
        chunks = fetch_chunks_without_embeddings(env, limit=args.limit)
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1

    if not chunks:
        logger.info("No chunks without embeddings — nothing to do.")
        return 0

    logger.info("Embedding %d chunks...", len(chunks))

    updated = 0
    skipped = 0
    failed = 0
    for ch in chunks:
        content = ch.get("content", "")
        if not content:
            skipped += 1
            continue

        vec = embed_with_retry(client, content)
        if vec is None:
            logger.warning(
                "embed failed for %s#%s",
                ch.get("source_id"),
                ch.get("chunk_index"),
            )
            failed += 1
            continue

        if args.dry_run:
            logger.info("would update %s#%s", ch.get("source_id"), ch.get("chunk_index"))
            continue

        if patch_embedding(env, ch["id"], vec):
            updated += 1
            if updated % 20 == 0:
                logger.info("updated %d chunks", updated)
        else:
            failed += 1

        if EMBED_DELAY_SEC:
            time.sleep(EMBED_DELAY_SEC)

    logger.info(
        "Done: embedded/updated %d chunks (%d skipped, %d failed)",
        updated,
        skipped,
        failed,
    )

    if updated and not args.dry_run:
        notify_knowledge_engine(updated)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
