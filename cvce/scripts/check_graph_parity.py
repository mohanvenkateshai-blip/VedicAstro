"""
Parity check: SQLiteKnowledgeStore vs SupabaseKnowledgeStore (B-56 migration
checklist §7 — "Verify parity" before flipping GRAPH_SOURCE=sqlite in prod).

Spot-checks N node ids (sampled from the baked DB, since that's always
available locally) against both backends and diffs their get_node()/
get_links() output. Requires SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in the
environment to reach the live Supabase side — this script is meant to be run
wherever those are available (a session/CI job with prod-equivalent creds),
not as part of the routine build.

Usage: python scripts/check_graph_parity.py [--sample 50] [--db knowledge_engine/graph.db]
Exit code 0 = parity confirmed; 1 = mismatches found; 2 = Supabase unreachable.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge_engine.store.sqlite_store import SQLiteKnowledgeStore  # noqa: E402
from knowledge_engine.store.supabase_store import SupabaseKnowledgeStore  # noqa: E402

# Fields that are EXPECTED to differ and shouldn't fail the check:
# - Supabase rows carry a live `updated_at`/`created_at`/`graph_version` the
#   baked snapshot doesn't (it has its own build-time meta instead).
# - `id`/`file_type`/`label`/domain fields must match exactly.
_IGNORE_KEYS = {"updated_at", "created_at", "graph_version"}


def _normalize(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in _IGNORE_KEYS and v is not None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=50)
    ap.add_argument("--db", default=None)
    args = ap.parse_args()

    if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        print("SKIP: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set — cannot reach the live store.")
        return 2

    sqlite_store = SQLiteKnowledgeStore(db_path=args.db)
    supabase_store = SupabaseKnowledgeStore()

    sqlite_stats = sqlite_store.get_stats()
    supabase_stats = supabase_store.get_stats()
    print(f"sqlite:   node_count={sqlite_stats['node_count']}  link_count={sqlite_stats['link_count']}")
    print(f"supabase: node_count={supabase_stats['node_count']}")

    all_nodes = sqlite_store.get_nodes_page(limit=sqlite_stats["node_count"])
    sample = random.sample(all_nodes, min(args.sample, len(all_nodes)))

    mismatches: list[str] = []
    for n in sample:
        node_id = n["id"]
        sb_node = supabase_store.get_node(node_id)
        if sb_node is None:
            mismatches.append(f"{node_id}: missing in Supabase")
            continue
        if _normalize(n) != _normalize(sb_node):
            mismatches.append(f"{node_id}: field mismatch\n  sqlite:   {_normalize(n)}\n  supabase: {_normalize(sb_node)}")

        sqlite_links = sorted(
            (l["source"], l["target"], l["relation"]) for l in sqlite_store.get_links(source_id=node_id, limit=1000)
        )
        sb_links = sorted(
            (l.get("source", l.get("source_id")), l.get("target"), l.get("relation"))
            for l in supabase_store.get_links(source_id=node_id, limit=1000)
        )
        if sqlite_links != sb_links:
            mismatches.append(f"{node_id}: link set mismatch (sqlite={len(sqlite_links)}, supabase={len(sb_links)})")

    if mismatches:
        print(f"\nFAIL: {len(mismatches)}/{len(sample)} sampled nodes mismatched:")
        for m in mismatches:
            print(f"  - {m}")
        return 1

    print(f"\nPASS: {len(sample)}/{len(sample)} sampled nodes match exactly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
