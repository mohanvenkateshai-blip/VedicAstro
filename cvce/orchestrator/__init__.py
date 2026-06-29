"""
Orchestration Engine — the 9th engine. Registry, Router, Manifest.

Every engine self-registers. The Orchestrator:
1. Maps user intent → engine
2. Tracks capabilities, inputs, outputs, dependencies
3. Auto-updates manifest when engines evolve
4. Provides lookup: "which engine handles X?"
"""

from __future__ import annotations

import json
import os
from typing import Optional

_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "engine-manifest.json")


class EngineRegistration:
    def __init__(
        self,
        id: str,
        name: str,
        purpose: str,
        endpoint: str,
        inputs: list,
        outputs: list,
        keywords: list,
        depends_on: list = None,
    ):
        self.id = id
        self.name = name
        self.purpose = purpose
        self.endpoint = endpoint
        self.inputs = inputs
        self.outputs = outputs
        self.keywords = keywords
        self.depends_on = depends_on or []
        self.version = "1.0.0"
        self.status = "active"


class Orchestrator:
    _instance: Orchestrator | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._engines = {}
            cls._instance._init_defaults()
        return cls._instance

    def _init_defaults(self):
        self.register(
            EngineRegistration(
                id="janma-kundali",
                name="Janma Kundali Engine",
                purpose="Compute complete birth chart from DOB+place: planets, signs, nakshatras, D1-D60 vargas, ashtakavarga, birth panchanga, pushkar navamsha",
                endpoint="/chart",
                inputs=["birth_datetime", "birth_lat", "birth_lon", "birth_tz"],
                outputs=["chart_data (full horoscope)"],
                keywords=[
                    "chart",
                    "birth",
                    "kundali",
                    "horoscope",
                    "janma",
                    "rasi",
                    "navamsa",
                    "varga",
                    "ashtakavarga",
                    "lagna",
                    "pushkar",
                ],
            )
        )
        self.register(
            EngineRegistration(
                id="gochar-phala",
                name="Gochar Phala Engine",
                purpose="Transit predictions: planet positions today, house-from-janma, vedha, tara balam, moorthi, sade-sati, latta, classical transit effects with source citations",
                endpoint="/predict",
                inputs=["chart_data", "query_date", "query_time"],
                outputs=[
                    "transit_verdicts, gochar_score, vedha_flags, tara_result, moorthi_result, sade_sati_status"
                ],
                keywords=[
                    "transit",
                    "gochar",
                    "today",
                    "prediction",
                    "vedha",
                    "tara",
                    "moorthi",
                    "sade sati",
                    "latta",
                    "chandra bala",
                ],
                depends_on=["janma-kundali"],
            )
        )
        self.register(
            EngineRegistration(
                id="dasha-phala",
                name="Dasha Phala Engine",
                purpose="Multi-system dasha computation: Vimshottari 5-level, Yogini, Ashtottari. Current period, pending balance, dasha lord effects, timeline",
                endpoint="/dashas",
                inputs=["birth_chart", "query_date"],
                outputs=["current_dasha, dasha_tree (5 levels), multi_system_view"],
                keywords=[
                    "dasha",
                    "dasa",
                    "vimshottari",
                    "yogini",
                    "ashtottari",
                    "period",
                    "maha",
                    "antar",
                    "pratyantar",
                    "sookshma",
                    "prana",
                    "bhukti",
                ],
                depends_on=["janma-kundali"],
            )
        )
        self.register(
            EngineRegistration(
                id="yoga-phala",
                name="Yoga Phala Engine",
                purpose="Detect active yogas in birth chart: Pancha Mahapurusha, Chandra, Raja, Dhana, Nabhasa, Special. 284-yoga classical catalog with descriptions",
                endpoint="/yogas",
                inputs=["chart_data"],
                outputs=["active_yogas, yoga_categories, classical_definitions"],
                keywords=[
                    "yoga",
                    "raja",
                    "dhana",
                    "mahapurusha",
                    "chandra",
                    "nabhasa",
                    "combination",
                    "pancha",
                    "ruchaka",
                    "hamsa",
                    "malavya",
                ],
                depends_on=["janma-kundali"],
            )
        )
        self.register(
            EngineRegistration(
                id="bala-nirnaya",
                name="Bala Nirnaya Engine",
                purpose="Planetary strength computation: Shadbala (6 components), Ashtakavarga bindus, dignity (exalted/own/debilitated/combust), vimshopaka, ishta/kashta phala",
                endpoint="/shadbala",
                inputs=["chart_data"],
                outputs=["shadbala_breakdown, dignity_map, strength_ranking, combust_flags"],
                keywords=[
                    "strength",
                    "bala",
                    "shadbala",
                    "dignity",
                    "exalted",
                    "debilitated",
                    "combust",
                    "bindus",
                    "power",
                    "weak",
                    "strong",
                ],
                depends_on=["janma-kundali"],
            )
        )
        self.register(
            EngineRegistration(
                id="muhurta-nirnaya",
                name="Muhurta Nirnaya Engine",
                purpose="Electional astrology: find best time window for specific activity. Panchanga filter, tara balam, chandrabala, lagna shuddhi, do-ghati muhurtas, rahu kalam avoidance",
                endpoint="/muhurta (standalone)",
                inputs=["activity_type", "date_range", "chart_data"],
                outputs=[
                    "ranked_muhurta_windows, panchanga_verdicts, tara_chandrabala_status, best_window"
                ],
                keywords=[
                    "muhurta",
                    "election",
                    "window",
                    "wedding",
                    "auspicious",
                    "shubh",
                    "time",
                    "rahu kalam",
                    "abhijit",
                    "brahma",
                ],
                depends_on=["janma-kundali", "gochar-phala"],
            )
        )
        self.register(
            EngineRegistration(
                id="koota-milan",
                name="Koota Milan Engine",
                purpose="Compatibility matching: 36-point Guna Milan (8 kootas), Kuja Dosha (Manglik) detection + cancellation, Nadi Dosha check, Graha Maitri analysis",
                endpoint="/koota-match",
                inputs=["bride_chart", "groom_chart"],
                outputs=["total_score/36, koota_breakdown, kuja_dosha_status, nadi_dosha_flag"],
                keywords=[
                    "compatibility",
                    "koota",
                    "matching",
                    "guna",
                    "milan",
                    "marriage",
                    "kuja dosha",
                    "manglik",
                    "nadi",
                    "bhakoot",
                    "gana",
                ],
                depends_on=["janma-kundali"],
            )
        )
        self.register(
            EngineRegistration(
                id="shastra-pramana",
                name="Shastra Pramana Engine",
                purpose="Classical citation retrieval: source text, chapter, verse for any astrological rule. Knowledge graph lookups for classical descriptions and text conflicts",
                endpoint="/rules/query",
                inputs=["rule_name, concept_name"],
                outputs=[
                    "classical_citations, text_sources, conflicting_views, sanskrit_originals"
                ],
                keywords=[
                    "citation",
                    "source",
                    "classical",
                    "text",
                    "verse",
                    "shastra",
                    "reference",
                    "bphs",
                    "phaladeepika",
                    "why",
                    "proof",
                    "pramana",
                ],
                depends_on=["janma-kundali"],
            )
        )

    def register(self, engine: EngineRegistration):
        self._engines[engine.id] = engine

    def resolve(self, query: str) -> dict:
        """Given a natural language query, find which engine(s) should handle it.

        Returns {engine_id, confidence, why} for the best match."""
        query_lower = query.lower()
        scored = []
        for eng in self._engines.values():
            score = 0
            matches = []
            for kw in eng.keywords:
                if kw in query_lower:
                    score += 1
                    matches.append(kw)
            if score > 0:
                scored.append(
                    {
                        "engine": eng.id,
                        "name": eng.name,
                        "score": score,
                        "matched_keywords": matches,
                        "endpoint": eng.endpoint,
                        "purpose": eng.purpose,
                    }
                )
        scored.sort(key=lambda x: -x["score"])
        return {
            "query": query,
            "results": scored[:3],
            "best_match": scored[0] if scored else None,
            "auto_fetch": f"POST {scored[0]['endpoint']}" if scored else None,
        }

    def manifest(self) -> dict:
        return {
            "version": "1.0.0",
            "total_engines": len(self._engines),
            "engines": [
                {
                    "id": e.id,
                    "name": e.name,
                    "purpose": e.purpose,
                    "endpoint": e.endpoint,
                    "inputs": e.inputs,
                    "outputs": e.outputs,
                    "keywords": e.keywords,
                    "depends_on": e.depends_on,
                    "version": e.version,
                    "status": e.status,
                }
                for e in self._engines.values()
            ],
            "how_to_use": {
                "find_engine": "POST /orchestrate {query: 'what will happen to me today?'}",
                "list_all": "GET /orchestrate/manifest",
                "test_engine": "GET /orchestrate/test/{engine_id}",
            },
        }

    def save_manifest(self):
        """Save engine manifest to disk. Skips silently if FS is read-only (Fly.io)."""
        try:
            with open(_MANIFEST_PATH, "w") as f:
                json.dump(self.manifest(), f, indent=2)
        except OSError:
            pass  # read-only filesystem (Fly.io container)

    def engine_for(self, feature: str) -> dict | None:
        resolution = self.resolve(feature)
        best = resolution.get("best_match")
        if best:
            eng = self._engines[best["engine"]]
            return {
                "engine_id": eng.id,
                "engine_name": eng.name,
                "endpoint": eng.endpoint,
                "inputs": eng.inputs,
                "outputs": eng.outputs,
                "purpose": eng.purpose,
                "depends_on": eng.depends_on,
            }
        return None


orchestrator = Orchestrator()
# Note: engine-manifest.json is for Handoff Engine consumption.
# On Fly.io (read-only FS), the file write is skipped gracefully.
