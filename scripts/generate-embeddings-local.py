#!/usr/bin/env python3
"""
Generate embeddings for corpus_chunks using LOCAL sentence-transformers (no Gemini).
Adapted for VedicAstro — runs entirely offline after model download.

Usage:
  source portal/.env.local
  python3 scripts/generate-embeddings-local.py [--limit N] [--model all-MiniLM-L6-v2]

Model options (dim):
  all-MiniLM-L6-v2 (384) — fast, good quality
  all-mpnet-base-v2 (768) — higher quality, slower
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
# cvce/ must lead sys.path so the app's local `knowledge_engine` package
# (with .integration) resolves — not a same-named third-party PyPI SDK that
# may be installed in the venv. Without this the post-embed reload
# notification silently no-ops ("No module named 'knowledge_engine.integration'").
sys.path.insert(0, str(ROOT / "cvce"))

from supabase_corpus_sync import api_request, load_env  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FETCH_PAGE = 500
MAX_RETRIES = 3
EMBED_DELAY_SEC = 0.02
DEFAULT_MODEL = "all-mpnet-base-v2"
EMBED_DIM = 768  # all-mpnet-base-v2


_model = None


def get_local_model(model_name: str = DEFAULT_MODEL):
    """Lazy-load sentence-transformers model (cached after first use)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading local embedding model: %s", model_name)
        _model = SentenceTransformer(model_name)
        logger.info("Model loaded. Embedding dim=%d", _model.get_sentence_embedding_dimension())
    return _model


def embed_text_local(text: str, model_name: str = DEFAULT_MODEL) -> list[float] | None:
    """Generate embedding using local sentence-transformers."""
    if not text or not text.strip():
        return None
    try:
        model = get_local_model(model_name)
        vec = model.encode(text[:8000], normalize_embeddings=True)
        return vec.tolist()
    except Exception as exc:
        logger.warning("embed_text_local failed (%s chars): %s", len(text), exc)
        return None


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
        logger.error("patch failed for %s: HTTP %s %s", chunk_id, code, repr(body[:120]))
        return False
    return False


def notify_knowledge_engine(chunk_count: int) -> None:
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="Max chunks to embed (0 = all)")
    ap.add_argument("--model", type=str, default=DEFAULT_MODEL, help="sentence-transformers model name")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    env = load_env()
    if not env.get("SUPABASE_URL") or not env.get("SUPABASE_SERVICE_ROLE_KEY"):
        logger.error("missing Supabase env (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)")
        return 1

    logger.info("Using LOCAL embeddings (sentence-transformers, model=%s, dim=%d)", args.model, EMBED_DIM)
    logger.info("No Gemini / external API calls will be made.")

    try:
        chunks = fetch_chunks_without_embeddings(env, limit=args.limit)
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1

    if not chunks:
        logger.info("No chunks without embeddings — nothing to do.")
        return 0

    logger.info("Embedding %d chunks locally...", len(chunks))

    updated = 0
    skipped = 0
    failed = 0
    for i, ch in enumerate(chunks, 1):
        content = ch.get("content", "")
        if not content or not content.strip():
            skipped += 1
            continue

        vec = embed_text_local(content, model_name=args.model)
        if vec is None:
            logger.warning("embed failed for %s#%s", ch.get("source_id"), ch.get("chunk_index"))
            failed += 1
            continue

        if args.dry_run:
            logger.info("would update %s#%s", ch.get("source_id"), ch.get("chunk_index"))
            continue

        if patch_embedding(env, ch["id"], vec):
            updated += 1
            if updated % 50 == 0:
                logger.info("updated %d/%d chunks", updated, len(chunks))
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

    # Final verification: count rows with embeddings
    try:
        path = "/rest/v1/corpus_chunks?select=count&embedding=not.is.null"
        code, body = api_request(env, "GET", path)
        if code == 200:
            total_with_emb = json.loads(body)[0].get("count", 0)
            logger.info("VERIFICATION: %s chunks now have embeddings in Supabase", total_with_emb)
    except Exception as exc:
        logger.warning("Verification count failed: %s", exc)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
