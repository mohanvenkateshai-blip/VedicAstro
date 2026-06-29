#!/usr/bin/env python3
"""
Orphan Node Resolver for Vedic Knowledge Graph

Identifies orphan nodes (nodes with zero connections) and proposes the top 3 most likely parents
using a combination of:
- Label + description similarity
- Community proximity
- LLM adjudication (Gemini)

Usage:
  source portal/.env.local
  python3 scripts/orphan-resolver.py --limit 50 --output orphan-proposals.json

Requirements:
  pip install google-genai
"""

import argparse
import json
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from google import genai
except ImportError:
    print("Please install: pip install google-genai")
    exit(1)


ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "knowledge-graph" / "graphify-out" / "graph.json"


def load_graph() -> Dict[str, Any]:
    return json.loads(GRAPH_PATH.read_text(encoding="utf-8"))


def find_orphans(graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    nodes = graph["nodes"]
    links = graph["links"]

    connected = set()
    for link in links:
        connected.add(link.get("source"))
        connected.add(link.get("target"))

    orphans = [n for n in nodes if n["id"] not in connected]
    return orphans


def get_node_text(node: Dict[str, Any]) -> str:
    """Create a rich text representation of a node for similarity."""
    parts = [node.get("label", "")]
    if "properties" in node:
        props = node["properties"]
        if isinstance(props, dict):
            for k, v in list(props.items())[:5]:
                parts.append(f"{k}: {v}")
    return " | ".join(str(p) for p in parts if p)


def find_similar_nodes(
    orphan: Dict[str, Any],
    graph: Dict[str, Any],
    top_k: int = 10
) -> List[Tuple[Dict[str, Any], float]]:
    """
    Find the most similar nodes using simple text overlap + community bonus.
    This is a lightweight fallback until real embeddings are ready.
    """
    orphan_text = get_node_text(orphan).lower()
    orphan_community = orphan.get("community")

    candidates = []
    for node in graph["nodes"]:
        if node["id"] == orphan["id"]:
            continue

        node_text = get_node_text(node).lower()
        # Simple overlap score
        overlap = len(set(orphan_text.split()) & set(node_text.split()))
        score = overlap

        # Bonus if same community
        if node.get("community") == orphan_community:
            score += 3

        if score > 0:
            candidates.append((node, score))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:top_k]


def ask_llm_for_parents(
    orphan: Dict[str, Any],
    candidates: List[Tuple[Dict[str, Any], float]],
    model: str = "gemini-2.0-flash"
) -> List[Dict[str, Any]]:
    """
    Use Gemini to pick the best parents from candidates.
    This function is now OPTIONAL. If LLM fails or is not available,
    the script will still produce useful output using only similarity candidates.
    """
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("No Gemini key found — skipping LLM step (will use similarity candidates only).")
        return []

    client = genai.Client(api_key=key)

    orphan_desc = get_node_text(orphan)
    candidate_text = "\n".join(
        f"- {c[0]['id']} | {get_node_text(c[0])[:120]} (score={c[1]})"
        for c in candidates
    )

    prompt = f"""You are an expert in Vedic astrology knowledge graphs.

Orphan node:
ID: {orphan['id']}
Description: {orphan_desc}

Top candidate nodes (with similarity scores):
{candidate_text}

Task:
Suggest up to 3 best parent nodes this orphan should connect to.
For each suggestion, provide:
- parent_id
- suggested_relation (e.g., "belongs_to_book", "part_of_topic", "instance_of_concept")
- confidence (0-1)
- short_reason (max 15 words)

Return ONLY valid JSON in this exact format:
{{
  "suggestions": [
    {{"parent_id": "...", "suggested_relation": "...", "confidence": 0.0, "reason": "..."}},
    ...
  ]
}}
"""

    try:
        resp = client.models.generate_content(model=model, contents=prompt)
        text = resp.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1].strip()
        result = json.loads(text)
        return result.get("suggestions", [])
    except Exception as e:
        print(f"LLM call failed for {orphan['id']}: {e} — falling back to similarity candidates only.")
        return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Process only first N orphans (0 = all)")
    parser.add_argument("--output", default="knowledge-graph/orphan-proposals.json")
    args = parser.parse_args()

    print("Loading graph...")
    graph = load_graph()

    print("Finding orphan nodes...")
    orphans = find_orphans(graph)
    print(f"Found {len(orphans)} orphan nodes.")

    if args.limit > 0:
        orphans = orphans[:args.limit]

    proposals = []

    for i, orphan in enumerate(orphans):
        print(f"[{i+1}/{len(orphans)}] Processing: {orphan['id']}")

        candidates = find_similar_nodes(orphan, graph, top_k=8)
        suggestions = ask_llm_for_parents(orphan, candidates)

        # Build final proposal — always include top_candidates,
        # and include llm_suggestions only if they exist
        proposal = {
            "orphan_id": orphan["id"],
            "orphan_label": orphan.get("label"),
            "community": orphan.get("community"),
            "top_candidates": [
                {"id": c[0]["id"], "label": c[0].get("label"), "score": c[1]}
                for c in candidates
            ],
        }

        if suggestions:
            proposal["llm_suggestions"] = suggestions
        else:
            # Fallback: promote top 3 similarity candidates as suggestions
            proposal["llm_suggestions"] = [
                {
                    "parent_id": c[0]["id"],
                    "suggested_relation": "related_to",
                    "confidence": round(min(c[1] / 10, 0.9), 2),
                    "reason": "High textual + community similarity (LLM unavailable)"
                }
                for c in candidates[:3]
            ]

        proposals.append(proposal)

        # Be nice to the API
        time.sleep(0.8)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(proposals, indent=2), encoding="utf-8")

    print(f"\n✓ Saved {len(proposals)} proposals to {output_path}")


if __name__ == "__main__":
    main()
