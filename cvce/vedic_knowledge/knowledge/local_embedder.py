"""Local ONNX embedder (fastembed) — single source of truth for the corpus
vector space, used for BOTH document indexing and query-time embedding so
they live in the same space (the mismatch that made prod search dormant).

Model: BAAI/bge-small-en-v1.5 (384-dim). Chosen over mpnet/bge-base because
it runs via ONNX Runtime (no torch → no ~1GB RAM), fits the free-tier 1GB
Fly machine (~324MB steady-state measured; app baseline ~282MB → ~606MB
total, ~400MB headroom), embeds better than mpnet on retrieval benchmarks,
and its 384-dim vectors are half the storage/search cost of 768-dim.

Lazy singleton: the model is loaded on first use, not at import — so
chart/dasha/etc. requests that never touch semantic search never pay the
RAM. Bake the model into the Docker image (pre-download) so Fly's ephemeral
FS doesn't re-fetch it on cold start.
"""

from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger(__name__)

LOCAL_EMBED_MODEL = os.environ.get("LOCAL_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
LOCAL_EMBED_DIM = 384

_model = None
_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from fastembed import TextEmbedding

                logger.info("Loading local embedder %s (first use)…", LOCAL_EMBED_MODEL)
                cache_dir = os.environ.get("FASTEMBED_CACHE_PATH")
                _model = (
                    TextEmbedding(model_name=LOCAL_EMBED_MODEL, cache_dir=cache_dir)
                    if cache_dir
                    else TextEmbedding(model_name=LOCAL_EMBED_MODEL)
                )
    return _model


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed passages for indexing. Empty/blank texts yield a zero vector so
    positional alignment with the caller's id list is preserved."""
    model = _get_model()
    cleaned = [(t or "").strip()[:8000] for t in texts]
    out: list[list[float]] = []
    # fastembed.embed is a generator; passage_embed adds the doc-side handling
    embed_fn = getattr(model, "passage_embed", None) or model.embed
    for vec in embed_fn(cleaned):
        out.append([float(x) for x in vec])
    return out


def embed_query(text: str) -> list[float] | None:
    """Embed a search query. bge asymmetric retrieval prefixes queries with a
    search instruction — fastembed's query_embed handles that; fall back to
    plain embed if unavailable."""
    text = (text or "").strip()
    if not text:
        return None
    model = _get_model()
    query_fn = getattr(model, "query_embed", None) or model.embed
    for vec in query_fn([text[:8000]]):
        return [float(x) for x in vec]
    return None
