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
from dataclasses import asdict
from typing import Optional

from vedic_engine.synthesis.transit_analyzer import TransitImpactAnalyzer
from .graph import GraphRAG


class PredictionEnhancer:
    """Enriches VedicPrediction results with graph knowledge."""

    def __init__(self):
        self.graph = GraphRAG()
        self._transit_analyzer = TransitImpactAnalyzer()

    def enhance(
        self,
        prediction_result,
        natal_sign: dict | None = None,
        janma_nakshatra: str | None = None,
        janma_rashi: str | None = None,
    ) -> dict:
        """Enrich a prediction result with graph-sourced data.

        Args:
            prediction_result: VedicPrediction dataclass or dict with
                panchanga, gochar, dasha, yogas, ashtakavarga fields.
            natal_sign: dict of planet → rashi_index (0=Aries), optional.
            janma_nakshatra: birth Moon nakshatra name, optional.
            janma_rashi: birth Moon rashi name, optional.

        Returns:
            Dict with keys: transit_citations, yoga_citations,
            text_conflicts, god_node_insights, graph_stats.
        """
        r = prediction_result
        yogas = getattr(r, "yogas", None) or []

        dasha_maha = None
        dasha_antar = None
        dasha_score = 0
        if hasattr(r, "dasha") and r.dasha:
            if r.dasha.current_mahadasha:
                dasha_maha = r.dasha.current_mahadasha.planet
            if r.dasha.current_antardasha:
                dasha_antar = r.dasha.current_antardasha.planet
            dasha_score = getattr(r.dasha, "dasha_score", 0) or 0

        transit_intel = None
        if hasattr(r, "gochar") and r.gochar:
            analyzed = self._transit_analyzer.analyze(
                r.gochar,
                natal_sign=natal_sign,
                dasha_maha=dasha_maha,
                dasha_antar=dasha_antar,
                dasha_score=dasha_score,
                ashtakavarga=getattr(r, "ashtakavarga", None),
            )
            if analyzed:
                transit_intel = asdict(analyzed)

        enhancement = {
            "transit_intelligence": transit_intel,
            "transit_citations": [],
            "yoga_citations": [],
            "text_conflicts": self._chart_conflicts(natal_sign, yogas),
            "god_node_insights": [],
            "graph_stats": self.graph.stats,
        }

        # Legacy citation blocks (secondary; UI prefers transit_intelligence)
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

        # 3b. Natal chart corpus matches (birth nakshatra / Moon sign)
        natal = self._natal_insights(janma_nakshatra, janma_rashi)
        if natal:
            enhancement["natal_insights"] = natal

        # 4. Panchanga-day activations
        if hasattr(r, "panchanga") and r.panchanga:
            pn = self._panchanga_insights(r.panchanga)
            if pn:
                enhancement["panchanga_insights"] = pn

        # 5. Muhurta yoga citations from graph
        if hasattr(r, "muhurta_yogas") and r.muhurta_yogas:
            enhancement["muhurta_citations"] = r.muhurta_yogas.get("active", [])

        return enhancement

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _normalize_effect_text(txt: str) -> str:
        """Strip graph extraction prefixes; keep readable classical prose."""
        txt = re.sub(r"\s+", " ", (txt or "").strip())
        txt = re.sub(r"^Life-area effect:\s*", "", txt, flags=re.I)
        txt = re.sub(r"^Benefic effect:\s*", "", txt, flags=re.I)
        txt = re.sub(r"^Malefic effect:\s*", "", txt, flags=re.I)
        return txt.strip()

    @staticmethod
    def _is_metadata_only(txt: str) -> bool:
        low = txt.lower()
        if not txt or len(txt) < 8:
            return True
        if "transit houses from moon" in low or "gochara vedha pairs" in low:
            return True
        if re.match(r"^\d+(st|nd|rd|th) house from moon", low):
            return True
        if low.startswith("vedha pairs:") and len(txt) < 120:
            return True
        return False

    def _filter_effects(self, effects: list, verdict: str) -> list:
        """Return up to 4 deduplicated, readable effects (metadata rows skipped)."""
        out: list[dict] = []
        seen: set[str] = set()
        for e in effects:
            raw = (e.get("effect") or "").strip()
            txt = self._normalize_effect_text(raw)
            if self._is_metadata_only(txt):
                continue
            key = txt.lower()[:72]
            if key in seen:
                continue
            seen.add(key)
            cleaned = dict(e)
            cleaned["effect"] = txt
            out.append(cleaned)
            if len(out) >= 4:
                break
        return out

    def _chart_conflicts(self, natal_sign: dict | None, yogas: list) -> list[dict]:
        """Contradictions mentioning this chart's planets or detected yogas."""
        all_c = self.graph.contradictions()
        if not natal_sign:
            return all_c[:8]
        keywords: set[str] = set()
        for p in natal_sign:
            if p and p != "Lagna":
                keywords.add(p.lower())
        for y in yogas:
            name = getattr(y, "name", str(y)).lower()
            for part in re.findall(r"[a-z]{4,}", name):
                keywords.add(part)
        matched = []
        for c in all_c:
            blob = f"{c.get('source', '')} {c.get('target', '')}".lower()
            if any(k in blob for k in keywords):
                matched.append(c)
        return (matched or all_c)[:8]

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
                if not info.get("descriptions"):
                    label = (info.get("label") or "").strip()
                    if label and len(label) > 24 and label.lower() != name.lower():
                        info["descriptions"] = [label]
                citations.append(info)
        return citations

    def _natal_insights(
        self,
        janma_nakshatra: str | None,
        janma_rashi: str | None,
    ) -> list[dict] | None:
        """Corpus passages for birth Moon nakshatra and sign."""
        insights: list[dict] = []
        if janma_nakshatra:
            matches = self._readable_matches(
                self.graph.search(f"{janma_nakshatra} nakshatra", top_n=6)
            )
            if matches:
                insights.append({
                    "type": "birth_nakshatra",
                    "value": janma_nakshatra,
                    "graph_matches": matches,
                })
        if janma_rashi:
            matches = self._readable_matches(
                self.graph.search(f"{janma_rashi} rashi moon", top_n=4)
            )
            if matches:
                insights.append({
                    "type": "birth_rashi",
                    "value": janma_rashi,
                    "graph_matches": matches,
                })
        return insights or None

    @staticmethod
    def _readable_matches(matches: list[dict] | None) -> list[dict]:
        """Drop header junk; keep labels that read like citations."""
        if not matches:
            return []
        out: list[dict] = []
        for m in matches:
            label = re.sub(r"\s+", " ", (m.get("label") or "").strip())
            if len(label) < 12 or len(label) > 220:
                continue
            if label.isupper() and len(label) > 40:
                continue
            if "\n\n" in label:
                label = label.split("\n\n")[0].strip()
            out.append({**m, "label": label})
            if len(out) >= 5:
                break
        return out

    def _god_node_insights(self, natal_sign: dict) -> list[dict]:
        """Find which god nodes (high-centrality concepts) are relevant.

        Maps natal planet positions to graph concepts for richest insight.
        """
        planets_in_chart = list(natal_sign.keys())
        gnodes = self.graph.god_nodes(top_n=15)

        relevant = []
        for gn in gnodes:
            raw_label = gn["label"]
            if not self._readable_label(raw_label):
                continue
            label = raw_label.lower()
            is_relevant = any(p.lower() in label for p in planets_in_chart if p != "Lagna")
            if is_relevant or any(
                r in label
                for r in [
                    "rasi", "nakshatra", "yoga", "lagna",
                    "tithi", "karana", "vedha", "sade sati",
                    "ashtakavarga", "neecha bhanga",
                ]
            ):
                neighbours = self.graph.neighbours(gn["id"], depth=1)
                concepts = [
                    self._normalize_effect_text(n.get("label", ""))
                    for n in neighbours["nodes"][:12]
                    if n.get("id") != gn["id"] and self._readable_label(n.get("label", ""))
                ]
                relevant.append({
                    "god_node": raw_label,
                    "degree": gn["degree"],
                    "community": gn["community"],
                    "connected_concepts": concepts[:8],
                })
        return relevant[:8]

    @staticmethod
    def _readable_label(label: str) -> bool:
        label = (label or "").strip()
        if len(label) < 4 or len(label) > 90:
            return False
        if label.isupper() and len(label) > 28:
            return False
        if label.count("\n") > 1:
            return False
        return True

    def _panchanga_insights(self, panchanga) -> list[dict] | None:
        """Search for graph insights based on today's panchanga values."""
        insights = []
        nak_name = getattr(panchanga, "nakshatra", "")
        if nak_name:
            search = self._readable_matches(
                self.graph.search(f"{nak_name} nakshatra", top_n=6)
            )
            if search:
                insights.append({
                    "type": "nakshatra",
                    "value": nak_name,
                    "graph_matches": search,
                })
        tithi = getattr(panchanga, "tithi_name", "")
        if tithi:
            search = self._readable_matches(
                self.graph.search(f"{tithi} tithi", top_n=4)
            )
            if search:
                insights.append({
                    "type": "tithi",
                    "value": tithi,
                    "graph_matches": search,
                })
        return insights or None
