#!/usr/bin/env python3
"""
Orphan Node Resolver for Vedic Knowledge Graph

Identifies orphan nodes (nodes with zero connections) and proposes the top 3 most likely parents
using a combination of:
- Label + description similarity
- Community proximity
- LLM adjudication (Gemini)

Usage:
  source portal/.env.local   # or export GEMINI_API_KEY
  python3 scripts/orphan-resolver.py --limit 50 --output knowledge-graph/orphan-proposals.json
  python3 scripts/orphan-resolver.py --resume --retry-llm   # upgrade similarity-only rows

Requirements:
  pip install google-genai
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "knowledge-graph" / "graphify-out" / "graph.json"
ENV_LOCAL = ROOT / "portal" / ".env.local"
DEFAULT_OUTPUT = ROOT / "knowledge-graph" / "orphan-proposals.json"

MAX_LLM_RETRIES = 4
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

log = logging.getLogger("orphan-resolver")


@dataclass
class RunStats:
    total: int = 0
    llm_ok: int = 0
    llm_failed: int = 0
    similarity_fallback: int = 0
    skipped_resume: int = 0
    no_candidates: int = 0
    llm_disabled_reason: str | None = None
    errors: list[str] = field(default_factory=list)


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def load_env_file() -> None:
    """Load GEMINI/GOOGLE keys from portal/.env.local when not already in the environment."""
    if not ENV_LOCAL.is_file():
        return
    for line in ENV_LOCAL.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in ("GEMINI_API_KEY", "GOOGLE_API_KEY") and value and not os.environ.get(key):
            os.environ[key] = value


def get_api_key() -> str | None:
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def get_genai_client():
    try:
        from google import genai
    except ImportError:
        log.error("google-genai not installed — run: pip install google-genai")
        return None

    key = get_api_key()
    if not key:
        log.warning("No GEMINI_API_KEY or GOOGLE_API_KEY — LLM step will be skipped")
        return None

    return genai.Client(api_key=key)


def load_graph() -> dict[str, Any]:
    if not GRAPH_PATH.is_file():
        raise FileNotFoundError(f"Graph not found: {GRAPH_PATH}")
    try:
        data = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {GRAPH_PATH}: {exc}") from exc
    if not isinstance(data, dict) or "nodes" not in data or "links" not in data:
        raise ValueError("Graph must contain 'nodes' and 'links' arrays")
    return data


def find_orphans(graph: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = graph.get("nodes", [])
    links = graph.get("links", [])

    connected: set[str] = set()
    for link in links:
        if not isinstance(link, dict):
            continue
        source = link.get("source")
        target = link.get("target")
        if source:
            connected.add(str(source))
        if target:
            connected.add(str(target))

    orphans = []
    for n in nodes:
        if not isinstance(n, dict) or "id" not in n:
            continue
        if str(n["id"]) not in connected:
            orphans.append(n)
    return orphans


def get_node_text(node: dict[str, Any]) -> str:
    """Create a rich text representation of a node for similarity."""
    parts = [node.get("label", "")]
    props = node.get("properties")
    if isinstance(props, dict):
        for k, v in list(props.items())[:5]:
            parts.append(f"{k}: {v}")
    return " | ".join(str(p) for p in parts if p)


def find_similar_nodes(
    orphan: dict[str, Any], graph: dict[str, Any], top_k: int = 10
) -> list[tuple[dict[str, Any], float]]:
    """Find the most similar nodes using text overlap + community bonus."""
    orphan_text = get_node_text(orphan).lower()
    orphan_community = orphan.get("community")

    candidates: list[tuple[dict[str, Any], float]] = []
    for node in graph["nodes"]:
        if node["id"] == orphan["id"]:
            continue

        node_text = get_node_text(node).lower()
        overlap = len(set(orphan_text.split()) & set(node_text.split()))
        score = float(overlap)

        if node.get("community") == orphan_community and orphan_community is not None:
            score += 3

        if score > 0:
            candidates.append((node, score))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:top_k]


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            inner = parts[1]
            if inner.startswith("json"):
                inner = inner[4:]
            return inner.strip()
    return text


def _extract_json_object(text: str) -> dict[str, Any]:
    """Parse LLM JSON, tolerating fences and trailing prose."""
    cleaned = _strip_markdown_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group(0))
        raise


def _error_message(exc: Exception) -> str:
    return str(exc).strip()


def _is_quota_exhausted(exc: Exception) -> bool:
    msg = _error_message(exc).lower()
    return any(
        token in msg
        for token in (
            "resource_exhausted",
            "credits are depleted",
            "billing",
            "insufficient quota",
            "exceeded your current quota",
        )
    )


def _is_retryable_error(exc: Exception) -> bool:
    if _is_quota_exhausted(exc):
        return False
    msg = _error_message(exc).lower()
    if any(token in msg for token in ("503", "502", "504", "500", "timeout", "temporarily unavailable")):
        return True
    if "429" in msg or "rate" in msg:
        return True
    code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    return code in RETRYABLE_STATUS_CODES


def _normalize_suggestions(raw: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in raw[:3]:
        if not isinstance(item, dict):
            continue
        parent_id = item.get("parent_id") or item.get("parent")
        if not parent_id:
            continue
        out.append(
            {
                "parent_id": str(parent_id),
                "suggested_relation": str(item.get("suggested_relation") or "related_to"),
                "confidence": float(item.get("confidence", 0.5)),
                "reason": str(item.get("reason") or item.get("short_reason") or "")[:120],
            }
        )
    return out


def similarity_fallback_suggestions(
    candidates: list[tuple[dict[str, Any], float]],
) -> list[dict[str, Any]]:
    return [
        {
            "parent_id": c[0]["id"],
            "suggested_relation": "related_to",
            "confidence": round(min(c[1] / 10, 0.9), 2),
            "reason": "High textual + community similarity (LLM unavailable)",
            "source": "similarity",
        }
        for c in candidates[:3]
    ]


def broader_fallback_suggestions(orphan: dict[str, Any], graph: dict[str, Any]) -> list[dict[str, Any]]:
    """Last-resort fallback: pick up to 3 nodes sharing any token in label."""
    orphan_label = str(orphan.get("label", "")).lower()
    tokens = set(orphan_label.split())
    if not tokens:
        return []
    matches: list[dict[str, Any]] = []
    for node in graph.get("nodes", []):
        if node.get("id") == orphan.get("id"):
            continue
        label = str(node.get("label", "")).lower()
        if tokens & set(label.split()):
            matches.append(
                {
                    "parent_id": node["id"],
                    "suggested_relation": "related_to",
                    "confidence": 0.3,
                    "reason": "Label token overlap (no similarity candidates)",
                    "source": "fallback",
                }
            )
            if len(matches) >= 3:
                break
    return matches


def ask_llm_for_parents(
    client,
    orphan: dict[str, Any],
    candidates: list[tuple[dict[str, Any], float]],
    *,
    model: str,
    stats: RunStats,
) -> list[dict[str, Any]]:
    """Use Gemini to pick the best parents from candidates. Returns [] on failure."""
    if client is None or stats.llm_disabled_reason:
        return []

    orphan_desc = get_node_text(orphan)
    candidate_text = "\n".join(
        f"- {c[0]['id']} | {get_node_text(c[0])[:120]} (score={c[1]})" for c in candidates
    )

    prompt = f"""You are an expert in Vedic astrology knowledge graphs.

Orphan node:
ID: {orphan["id"]}
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

    last_err = ""
    for attempt in range(MAX_LLM_RETRIES):
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            text = (getattr(resp, "text", None) or "").strip()
            if not text:
                raise ValueError("empty LLM response")

            result = _extract_json_object(text)
            suggestions = _normalize_suggestions(result.get("suggestions", []))
            if not suggestions:
                raise ValueError("LLM returned no usable suggestions")

            for s in suggestions:
                s["source"] = "llm"
            stats.llm_ok += 1
            return suggestions

        except Exception as exc:
            last_err = _error_message(exc)
            if _is_quota_exhausted(exc):
                stats.llm_disabled_reason = (
                    "Gemini quota/billing exhausted — using similarity fallback for remaining orphans"
                )
                log.error("%s Disabling further LLM calls.", stats.llm_disabled_reason)
                break
            if attempt < MAX_LLM_RETRIES - 1 and _is_retryable_error(exc):
                delay = 2**attempt
                log.warning(
                    "LLM retry %s/%s for %s (%s) — sleeping %ss",
                    attempt + 1,
                    MAX_LLM_RETRIES,
                    orphan["id"],
                    exc,
                    delay,
                )
                time.sleep(delay)
                continue
            break

    stats.llm_failed += 1
    stats.errors.append(f"{orphan['id']}: {last_err}")
    log.warning("LLM failed for %s after retries: %s", orphan["id"], last_err)
    return []


def is_similarity_only(proposal: dict[str, Any]) -> bool:
    suggestions = proposal.get("llm_suggestions") or []
    if not suggestions:
        return True
    return all(
        s.get("source") == "similarity"
        or "LLM unavailable" in str(s.get("reason", ""))
        for s in suggestions
    )


def load_existing_proposals(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        log.warning("Could not parse existing proposals at %s: %s", path, exc)
        return {}
    return {row["orphan_id"]: row for row in rows if row.get("orphan_id")}


def build_proposal(
    orphan: dict[str, Any],
    candidates: list[tuple[dict[str, Any], float]],
    llm_suggestions: list[dict[str, Any]],
    stats: RunStats,
    graph: dict[str, Any],
) -> dict[str, Any]:
    orphan_id = str(orphan.get("id", ""))
    proposal: dict[str, Any] = {
        "orphan_id": orphan_id,
        "orphan_label": orphan.get("label"),
        "community": orphan.get("community"),
        "top_candidates": [
            {"id": c[0]["id"], "label": c[0].get("label"), "score": c[1]} for c in candidates
        ],
    }

    if llm_suggestions:
        proposal["llm_suggestions"] = llm_suggestions
        proposal["resolution_source"] = "llm"
    elif candidates:
        proposal["llm_suggestions"] = similarity_fallback_suggestions(candidates)
        proposal["resolution_source"] = "similarity"
        stats.similarity_fallback += 1
    else:
        fallback = broader_fallback_suggestions(orphan, graph)
        proposal["llm_suggestions"] = fallback
        proposal["resolution_source"] = "fallback" if fallback else "none"
        if not fallback:
            stats.no_candidates += 1

    return proposal


def save_proposals(path: Path, proposals_by_id: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(proposals_by_id.values(), key=lambda p: p["orphan_id"])
    path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def print_summary(stats: RunStats, output_path: Path, orphan_count: int) -> None:
    log.info("--- Orphan resolver summary ---")
    log.info("Graph orphans: %s", orphan_count)
    log.info("Processed this run: %s", stats.total)
    log.info("LLM success: %s", stats.llm_ok)
    log.info("LLM failed (used similarity): %s", stats.llm_failed)
    log.info("Similarity-only (no key / empty candidates): %s", stats.similarity_fallback)
    log.info("Skipped (resume): %s", stats.skipped_resume)
    log.info("No similarity candidates: %s", stats.no_candidates)
    if stats.llm_disabled_reason:
        log.info("LLM disabled: %s", stats.llm_disabled_reason)
    log.info("Output: %s", output_path)
    if stats.errors:
        log.info("Sample errors (%s total):", len(stats.errors))
        for err in stats.errors[:5]:
            log.info("  • %s", err)


def main() -> int:
    parser = argparse.ArgumentParser(description="Propose parent links for orphan graph nodes")
    parser.add_argument("--limit", type=int, default=0, help="Process only first N orphans (0 = all)")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON path")
    parser.add_argument("--model", default="gemini-2.0-flash", help="Gemini model id")
    parser.add_argument("--delay", type=float, default=0.8, help="Seconds between LLM calls")
    parser.add_argument("--resume", action="store_true", help="Keep existing proposals; skip finished orphans")
    parser.add_argument(
        "--retry-llm",
        action="store_true",
        help="Re-run LLM for rows that only have similarity fallback",
    )
    parser.add_argument(
        "--checkpoint",
        type=int,
        default=25,
        help="Save output every N processed orphans (0 = save only at end)",
    )
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    configure_logging(args.verbose)
    load_env_file()

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    stats = RunStats()
    existing = load_existing_proposals(output_path) if (args.resume or args.retry_llm) else {}

    log.info("Loading graph from %s", GRAPH_PATH)
    graph = load_graph()

    log.info("Finding orphan nodes...")
    orphans = find_orphans(graph)
    log.info("Found %s orphan nodes", len(orphans))

    if args.limit > 0:
        orphans = orphans[: args.limit]

    client = get_genai_client()
    proposals_by_id = dict(existing)

    for i, orphan in enumerate(orphans):
        if not isinstance(orphan, dict) or "id" not in orphan:
            continue
        orphan_id = str(orphan["id"])
        prior = existing.get(orphan_id)

        if args.resume and prior and not args.retry_llm:
            stats.skipped_resume += 1
            continue

        if args.retry_llm and prior and not is_similarity_only(prior):
            stats.skipped_resume += 1
            continue

        log.info("[%s/%s] Processing %s", i + 1, len(orphans), orphan_id)
        stats.total += 1

        try:
            candidates = find_similar_nodes(orphan, graph, top_k=8)
            log.debug("Found %d similarity candidates for %s", len(candidates), orphan_id)
            llm_suggestions = ask_llm_for_parents(
                client, orphan, candidates, model=args.model, stats=stats
            )
            proposal = build_proposal(orphan, candidates, llm_suggestions, stats, graph)
            proposals_by_id[orphan_id] = proposal
        except Exception as exc:
            stats.errors.append(f"{orphan_id}: {type(exc).__name__}: {_error_message(exc)}")
            log.error("Failed processing %s: %s", orphan_id, exc)
            proposals_by_id[orphan_id] = {
                "orphan_id": orphan_id,
                "orphan_label": orphan.get("label"),
                "community": orphan.get("community"),
                "top_candidates": [],
                "llm_suggestions": [],
                "resolution_source": "error",
            }

        if args.checkpoint and stats.total % args.checkpoint == 0:
            save_proposals(output_path, proposals_by_id)
            log.info("Checkpoint saved (%s proposals)", len(proposals_by_id))

        if client is not None and not stats.llm_disabled_reason and args.delay > 0:
            time.sleep(args.delay)

    save_proposals(output_path, proposals_by_id)
    print_summary(stats, output_path, len(find_orphans(graph)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
