#!/usr/bin/env python3
"""
Minimal live verification for corpus_chunks embeddings + KnowledgeEngine.search().

Intended to run AFTER embeddings population + patches applied.

Usage:
  python3 scripts/verify_knowledge_embeddings.py
  CVCE_BASE_URL=... python3 ...   # or run inside cvce env with SUPABASE_* keys

Checks:
- vector_search_available() == True
- real ke.search / search_knowledge for 4 terms returns hits carrying source_id (+ similarity when vector)
- optional chapter provenance lookup on a sample node (from search result or direct)

Exits non-zero on hard failures. Prints PASS/FAIL summary.
Safe to run in CI after populate step (gated by real data presence).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
# Make "knowledge_engine.*" importable (cvce/ is the package root for KE modules)
cvce_dir = ROOT / "cvce"
if str(cvce_dir) not in sys.path:
    sys.path.insert(0, str(cvce_dir))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0


def ok(msg: str) -> None:
    global PASS
    print(f"  PASS: {msg}")
    PASS += 1


def bad(msg: str) -> None:
    global FAIL
    print(f"  FAIL: {msg}")
    FAIL += 1


def main() -> int:
    print("verify_knowledge_embeddings — live KE search + provenance")
    print(f"root={ROOT}")

    try:
        from knowledge_engine.integration import (
            get_knowledge_engine,
            search_knowledge,
            get_hierarchy_for_node,
        )
    except Exception as exc:
        bad(f"cannot import KE integration: {exc}")
        print(f"\nResult: {PASS} passed, {FAIL} failed")
        return 1

    ke = get_knowledge_engine()

    # 1) vector flag
    try:
        v = ke.vector_search_available()
        if v:
            ok("vector_search_available() == True")
        else:
            bad("vector_search_available() == False (embeddings not populated or store not wired)")
    except Exception as exc:
        bad(f"vector_search_available raised: {exc}")

    # 2) real searches (3-4 terms)
    queries = ["dasha", "muhurta", "yoga", "ashtakavarga"]
    sample_source_ids: list[str] = []
    for q in queries:
        try:
            # Prefer integration wrapper (exercises full path)
            hits = search_knowledge(q, top_k=4) or []
            if not hits:
                # direct fallback
                hits = ke.search(q, top_k=4) or []
            if not hits:
                bad(f"search({q!r}) returned 0 hits")
                continue
            ok(f"search({q!r}) → {len(hits)} hit(s)")
            for h in hits[:2]:
                sid = h.get("source_id")
                sim = h.get("similarity")
                if sid:
                    sample_source_ids.append(str(sid))
                    ok(f"  hit has source_id={sid[:60]}...")
                else:
                    bad(f"  hit missing source_id for {q}")
                if sim is not None:
                    ok(f"  hit has similarity={sim}")
                # content presence is soft
                if h.get("content"):
                    pass
        except Exception as exc:
            bad(f"search({q!r}) errored: {exc}")

    # 3) optional chapter-provenance enriched node
    # Use a hit's source_id if it looks like a node id, else try a couple known patterns
    checked_hier = False
    candidates = list(dict.fromkeys(sample_source_ids))[:3]  # dedup order-preserve
    # also try a couple common node-ish ids that patches likely cover
    candidates += ["node:bphs:ch-48", "BPHS-ch-48", "node:jaimini:ch-1-1"]

    for cand in candidates:
        if not cand or checked_hier:
            continue
        try:
            hier = get_hierarchy_for_node(cand)
            if hier and (hier.get("chapter_id") or hier.get("hierarchy_path")):
                ok(f"get_hierarchy_for_node({cand}) → chapter={hier.get('chapter_id')} path={hier.get('hierarchy_path')}")
                checked_hier = True
            elif hier:
                # partial
                ok(f"get_hierarchy_for_node({cand}) returned partial map")
                checked_hier = True
        except Exception:
            pass

    if not checked_hier:
        # Not a hard fail; provenance on nodes is orthogonal to chunk embeddings but exercised together
        print("  INFO: no chapter-provenance sample verified in this run (optional; depends on patch + node ids present)")

    print(f"\nResult: {PASS} passed, {FAIL} failed")
    if FAIL > 0:
        print("Embeddings may not be live, or store/KE not fully wired for corpus_chunks.")
        print("Recommended next: check Supabase corpus_chunks has embedding!=null rows, then re-run notify + this script.")
        return 1
    print("All core checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
