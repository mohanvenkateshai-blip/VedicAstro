"""GraphRAG — Knowledge-graph-powered Vedic prediction enhancer.

Loads the offline graph.json knowledge graph (448 nodes, 1,236 edges, 36
communities across 4 classical texts) and provides semantic search + traversal
APIs for enriching predictions with classical citations.

Philosophy:
- The graph is a **lookup layer** — it retrieves classical text knowledge.
- It does NOT replace the vedic_engine computation modules.
- Every enrichment adds a `graph_citation` field with source text & confidence.
"""

from .enhancer import PredictionEnhancer
from .graph import GraphRAG
from .rules_provider import GraphTransitRules, active_transit_rules, graph_rules_enabled

__all__ = [
    "GraphRAG",
    "PredictionEnhancer",
    "GraphTransitRules",
    "graph_rules_enabled",
    "active_transit_rules",
]
