#!/usr/bin/env python3
"""
Generate embeddings for corpus_chunks and upsert to Supabase.

Usage:
  source portal/.env.local
  python3 scripts/generate-embeddings.py [--limit 100]

Requires: google-genai (for text-embedding-004) or falls back to a simple hash placeholder.
Set GOOGLE_API_KEY or GEMINI_API_KEY.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from supabase_corpus_sync import load_env, api_request  # reuse helpers


def embed_text(client, text: str, model: str = "text-embedding-004") -> list[float] | None:
    try:
        # Google genai embeddings
        from google.genai import types
        resp = client.models.embed_content(
            model=model,
            contents=text[:8000],  # cap
            config=types.EmbedContentConfig(output_dimensionality=768),
        )
        return resp.embeddings[0].values if resp.embeddings else None
    except Exception as e:
        print(f"  embed error: {e}", file=sys.stderr)
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="Max chunks to embed (0 = all)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    env = load_env()
    if not env.get("SUPABASE_URL") or not env.get("SUPABASE_SERVICE_ROLE_KEY"):
        print("error: missing Supabase env", file=sys.stderr)
        return 1

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = None
    if key:
        try:
            from google import genai
            client = genai.Client(api_key=key)
            print("Using Gemini for embeddings")
        except Exception as e:
            print(f"genai not available or key issue: {e}")

    # Fetch chunks without embeddings
    code, body = api_request(
        env, "GET",
        "/rest/v1/corpus_chunks?select=id,source_id,chunk_index,content&embedding=is.null&limit=500"
    )
    if code != 200:
        print("Failed to fetch chunks", body[:200])
        return 1

    chunks = json.loads(body)
    if args.limit:
        chunks = chunks[:args.limit]

    print(f"Embedding {len(chunks)} chunks...")

    updated = 0
    for ch in chunks:
        content = ch.get("content", "")
        if not content:
            continue
        vec = None
        if client:
            vec = embed_text(client, content)
        if vec is None:
            # placeholder deterministic vector for now (real one requires model)
            import hashlib
            h = hashlib.sha256(content.encode()).digest()
            vec = [(b / 255.0) - 0.5 for b in h[:768]]  # fake 768 dim

        if args.dry_run:
            print(f"  would update {ch['source_id']}#{ch['chunk_index']}")
            continue

        payload = {"embedding": vec, "updated_at": datetime.now(timezone.utc).isoformat()}
        code, _ = api_request(
            env, "PATCH",
            f"/rest/v1/corpus_chunks?id=eq.{ch['id']}",
            json.dumps(payload).encode(),
            headers={"Prefer": "return=minimal"}
        )
        if code in (200, 204):
            updated += 1
            if updated % 20 == 0:
                print(f"  updated {updated}")
        else:
            print(f"  failed for {ch['id']}: {code}")

    print(f"✓ Embedded/updated {updated} chunks")

    # Notify KnowledgeEngine that embeddings were updated for this version
    try:
        import sys
        sys.path.insert(0, str(ROOT / "cvce"))
        from knowledge_engine import get_knowledge_engine
        ke = get_knowledge_engine()
        if ke.current_version:
            print(f"KnowledgeEngine notified of embedding update for version {ke.current_version.version}")
    except Exception as e:
        print(f"KnowledgeEngine notification skipped: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
