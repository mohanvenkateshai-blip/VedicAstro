"""Shim — GraphRAG lives in the shared `vedic-knowledge` package.

Backward-compatible re-export so existing `from graph_rag.graph import GraphRAG`
 imports keep working. Prefer:

     from vedic_knowledge import get_knowledge_graph
"""

from __future__ import annotations

import os
from pathlib import Path

# Default graph path for this host app when env is unset
_DEFAULT = Path(__file__).resolve().parent / "graph.json"
if _DEFAULT.is_file() and not os.environ.get("GRAPH_JSON_PATH") and not os.environ.get(
    "GRAPHIFY_GRAPH_PATH"
):
    os.environ["GRAPH_JSON_PATH"] = str(_DEFAULT)

from vedic_knowledge.graph.graph import (  # noqa: E402
    GraphRAG,
    GraphVersionMismatchError,
    check_graph_version,
    read_graph_metadata,
    resolve_graph_path,
    _tokenize,
)

__all__ = [
    "GraphRAG",
    "GraphVersionMismatchError",
    "check_graph_version",
    "read_graph_metadata",
    "resolve_graph_path",
    "_tokenize",
]
