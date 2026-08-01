"""Startup gate: refuse to serve if GRAPH_VERSION mismatches graph.json."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def apply_default_graph_path() -> None:
    """Point GRAPH_JSON_PATH at cvce/graph_rag/graph.json when unset."""
    if os.environ.get("GRAPH_JSON_PATH") or os.environ.get("GRAPHIFY_GRAPH_PATH"):
        return
    candidate = Path(__file__).resolve().parents[1] / "graph_rag" / "graph.json"
    if candidate.is_file():
        os.environ["GRAPH_JSON_PATH"] = str(candidate)


def enforce_at_startup(*, strict: bool | None = None) -> dict:
    """
    Call during app startup.

    strict defaults to True when GRAPH_VERSION is set, else False
    (missing graph is a warning, not a crash, unless GRAPH_VERSION_REQUIRED=1).
    """
    apply_default_graph_path()
    from vedic_knowledge import GraphVersionMismatchError, enforce_graph_version

    if strict is None:
        strict = bool(os.environ.get("GRAPH_VERSION")) or os.environ.get(
            "GRAPH_VERSION_REQUIRED", ""
        ).strip().lower() in ("1", "true", "yes", "on")
    try:
        result = enforce_graph_version(strict=strict)
    except GraphVersionMismatchError:
        raise
    if not result.get("ok"):
        logger.warning("graph version gate: %s", result.get("message"))
    else:
        logger.info("graph version gate: %s", result.get("message"))
    return result
