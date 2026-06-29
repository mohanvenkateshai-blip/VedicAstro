"""
Temporary integration helpers.

Goal: Start routing important graph access through the new KnowledgeEngine
instead of directly to GraphRAG or raw modules.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from .engine import KnowledgeEngine


@lru_cache(maxsize=1)
def get_knowledge_engine() -> KnowledgeEngine:
    """Singleton accessor for the central KnowledgeEngine."""
    return KnowledgeEngine()


def get_safe_transit_rules():
    """Preferred way for engines to get current validated transit rules."""
    ke = get_knowledge_engine()
    # For now we still delegate to the old provider, but we can add validity checks here.
    from graph_rag.rules_provider import active_transit_rules
    if not ke.is_knowledge_healthy():
        return None
    return active_transit_rules()


def get_safe_muhurta_rules():
    ke = get_knowledge_engine()
    from graph_rag.muhurta_rules_provider import active_muhurta_rules
    if not ke.is_knowledge_healthy():
        return None
    return active_muhurta_rules()
