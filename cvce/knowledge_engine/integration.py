"""Shim — preferred gateway re-exported from `vedic-knowledge`.

Full KnowledgeEngine still lives in this package (`engine.py`); the shared
package delegates to it when importable, and falls back to GraphRAG alone
when running outside VedicAstro.
"""

from __future__ import annotations

import os
from pathlib import Path

# Ensure host graph.json is visible to the shared package
_DEFAULT_GRAPH = Path(__file__).resolve().parents[1] / "graph_rag" / "graph.json"
if _DEFAULT_GRAPH.is_file() and not os.environ.get("GRAPH_JSON_PATH") and not os.environ.get(
    "GRAPHIFY_GRAPH_PATH"
):
    os.environ["GRAPH_JSON_PATH"] = str(_DEFAULT_GRAPH)

from vedic_knowledge.knowledge.integration import (  # noqa: E402, F401
    clear_knowledge_engine_cache,
    ensure_engine_registration,
    get_hierarchy_for_node,
    get_knowledge_engine,
    get_llm_narration,
    get_nodes_for_chapter,
    get_prediction_enhancer,
    get_registered_engines_with_status,
    get_safe_graph,
    get_safe_knowledge,
    get_safe_muhurta_rules,
    get_safe_nodes_for_chapter,
    get_safe_structured_book,
    get_safe_transit_rules,
    get_structured_book,
    get_structured_coverage,
    invalidate_chapter,
    invalidate_nodes,
    is_knowledge_healthy,
    notify_embeddings_updated,
    query_research_knowledge,
    rebuild_and_remap_structured,
    rebuild_structured_library,
    remap_nodes_to_structured,
    search_knowledge,
)

__all__ = [
    "clear_knowledge_engine_cache",
    "get_knowledge_engine",
    "get_safe_graph",
    "get_safe_transit_rules",
    "get_safe_muhurta_rules",
    "get_safe_knowledge",
    "is_knowledge_healthy",
    "search_knowledge",
    "query_research_knowledge",
    "notify_embeddings_updated",
    "get_prediction_enhancer",
    "get_llm_narration",
    "get_structured_book",
    "get_safe_structured_book",
    "get_nodes_for_chapter",
    "get_safe_nodes_for_chapter",
    "get_hierarchy_for_node",
    "rebuild_structured_library",
    "remap_nodes_to_structured",
    "rebuild_and_remap_structured",
    "invalidate_nodes",
    "invalidate_chapter",
    "get_structured_coverage",
    "get_registered_engines_with_status",
    "ensure_engine_registration",
]
