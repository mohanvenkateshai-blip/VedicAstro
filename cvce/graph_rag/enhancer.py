"""
enhancer.py — Enrich prediction engine output with graph-sourced classical
citations, text effects, and conflict notes.

Takes a VedicPrediction result + optional context (planet positions,
activity name) and returns enriched output with:
  - transit_citations: classical source-backed transit effects per planet
  - yoga_citations: classical definitions for detected yogas
  - text_conflicts: known contradictions between classical authorities
  - god_node_insights: key concepts (god nodes) most relevant to this chart
  - graph_stats: metadata about graph coverage
"""

from __future__ import annotations

import re
from typing import Optional

from .graph import GraphRAG


class PredictionEnhancer:
    """Enriches VedicPrediction results with graph knowledge."""

    def __init__(self):
        self.graph = GraphRAG()

    def enhance(self, prediction_result, natal_sign: dict | None = None) -> dict:
        """Enrich a prediction result with graph-sourced data.

        Args:
            prediction_result: VedicPrediction dataclass or dict with
                panchanga, gochar, dasha, yogas, ashtakavarga fields.
            natal_sign: dict of planet → rashi_index (0=Aries), optional.

        Returns:
            Dict with keys: transit_citations, yoga_citations,
            text_conflicts, god_node_insights, graph_stats.
        """
        r = prediction_result
        enhancement = {
            "transit_citations": [],
            "yoga_citations": [],
            "text_conflicts": self.graph.contradictions()[:10],
            "god_node_insights": [],
            "graph_stats": self.graph.stats,
        }

        # 1. Transit effect citations
        if hasattr(r, "gochar") and r.gochar and r.gochar.planet_predictions:
            enhancement["transit_citations"] = self._transit_citations(
                r.gochar.planet_predictions
            )

        # 2. Yoga classical descriptions
        if hasattr(r, "yogas") and r.yogas:
            enhancement["yoga_citations"] = self._yoga_citations(r.yogas)

        # 3. God nodes most relevant to natal chart
        if natal_sign:
            enhancement["god_node_insights"] = self._god_node_insights(natal_sign)

        # 4. Panchanga-day activations
        if hasattr(r, "panchanga") and r.panchanga:
            pn = self._panchanga_insights(r.panchanga)
            if pn:
                enhancement["panchanga_insights"] = pn

        return enhancement

    # ── Private helpers ───────────────────────────────────────────────────

    def _filter_effects(self, effects: list, verdict: str) -> list:
        """Return at most 4 deduplicated, readable effects (skip graph metadata noise)."""
        out: list[dict] = []
        seen: set[str] = set()
        skip_re = (
            "transit houses from moon",
            "gochara vedha pairs",
            "life-area effect:",
            "benefic effect:",
            "malefic effect:",
        )
        for e in effects:
            txt = (e.get("effect") or "").strip()
            low = txt.lower()
            if not txt or any(s in low for s in skip_re):
                continue
            if re.match(r"^\d+(st|nd|rd|th) house from moon", low):
                continue
            key = low[:72]
            if key in seen:
                continue
            seen.add(key)
            out.append(e)
            if len(out) >= 4:
                break
        return out

    def _transit_citations(self, planet_predictions: list) -> list[dict]:
        """For each transiting planet, find classical effect descriptions."""
        citations = []
        for pp in planet_predictions:
            planet = getattr(pp, "planet", "")
            house = getattr(pp, "house_from_janma", None)
            if not planet:
                continue
            effects = self.graph.transit_effects(planet, house)
            vedha_info = self.graph.vedha(planet)
            entry = {
                "planet": planet,
                "rashi": getattr(pp, "rashi", ""),
                "house_from_janma": house,
                "verdict": getattr(pp, "verdict", "neutral"),
                "classical_effects": [
                    {
                        "description": e["effect"],
                        "source": e.get("source", ""),
                        "confidence": e.get("confidence", 1.0),
                        "relation": e.get("relation", ""),
                    }
                    for e in self._filter_effects(effects, getattr(pp, "verdict", "neutral"))
                ],
            }
            if vedha_info:
                entry["vedha_pairs"] = vedha_info.get("vedha_pairs", "")
                entry["vedha_source"] = vedha_info.get("source", "")
            citations.append(entry)
        return citations

    def _yoga_citations(self, yogas: list) -> list[dict]:
        """For each detected yoga, look up classical definition & hyperedges."""
        citations = []
        for y in yogas:
            name = getattr(y, "name", str(y))
            info = self.graph.yoga_info(name)
            if not info:
                search = self.graph.search(name, top_n=3)
                if search:
                    info = {"yoga": name, "search_matches": search}
            if info:
                citations.append(info)
        return citations

    def _god_node_insights(self, natal_sign: dict) -> list[dict]:
        """Find which god nodes (high-centrality concepts) are relevant.

        Maps natal planet positions to graph concepts for richest insight.
        """
        planets_in_chart = list(natal_sign.keys())
        gnodes = self.graph.god_nodes(top_n=15)

        relevant = []
        for gn in gnodes:
            label = gn["label"].lower()
            is_relevant = any(p.lower() in label for p in planets_in_chart)
            if is_relevant or any(
                r in label
                for r in [
                    "rasi", "nakshatra", "yoga", "lagna",
                    "tithi", "karana", "vedha", "sade sati",
                    "ashtakavarga", "neecha bhanga",
                ]
            ):
                neighbours = self.graph.neighbours(gn["id"], depth=1)
                relevant.append({
                    "god_node": gn["label"],
                    "degree": gn["degree"],
                    "community": gn["community"],
                    "connected_concepts": [
                        n.get("label", "")
                        for n in neighbours["nodes"][:12]
                        if n.get("id") != gn["id"]
                    ],
                })
        return relevant[:8]

    def _panchanga_insights(self, panchanga) -> list[dict] | None:
        """Search for graph insights based on today's panchanga values."""
        insights = []
        nak_name = getattr(panchanga, "nakshatra", "")
        if nak_name:
            search = self.graph.search(f"{nak_name} nakshatra", top_n=5)
            if search:
                insights.append({
                    "type": "nakshatra",
                    "value": nak_name,
                    "graph_matches": search,
                })
        tithi = getattr(panchanga, "tithi_name", "")
        if tithi:
            search = self.graph.search(f"{tithi} tithi", top_n=3)
            if search:
                insights.append({
                    "type": "tithi",
                    "value": tithi,
                    "graph_matches": search,
                })
        return insights or None
