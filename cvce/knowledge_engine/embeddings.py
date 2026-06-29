"""Shared embedding helpers for corpus vector search."""

from __future__ import annotations

import os
from typing import Any

EMBED_MODEL = "text-embedding-004"
EMBED_DIM = 768


def get_genai_client() -> Any | None:
    """Return a Google GenAI client when an API key is configured."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return None
    try:
        from google import genai

        return genai.Client(api_key=key)
    except Exception:
        return None


def embed_text(
    client: Any,
    text: str,
    *,
    model: str = EMBED_MODEL,
    dim: int = EMBED_DIM,
) -> list[float] | None:
    """Embed text using Google text-embedding-004 (768-dim)."""
    if not text or client is None:
        return None
    try:
        from google.genai import types

        resp = client.models.embed_content(
            model=model,
            contents=text[:8000],
            config=types.EmbedContentConfig(output_dimensionality=dim),
        )
        if resp.embeddings:
            return list(resp.embeddings[0].values)
    except Exception:
        return None
    return None
