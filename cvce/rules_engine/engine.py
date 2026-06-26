"""
RuleEngine — fast O(1) dict-based rule lookups. No complex logic.

Design: Every rule is indexed by an obvious key (planet name, house number,
nakshatra name, tithi number, etc.). The engine pre-builds all indices at
load time so queries are instant.

Usage:
    engine = RuleEngine()
    # Transit: what happens when Jupiter is in 5th from natal Moon?
    engine.transit("Jupiter", 5)
    # → {"verdict": "bad", "type": "worst", "source": "GPD-Ch10-Table12"}
    
    # Yoga: does this chart have Hamsa Yoga?
    engine.yoga_condition("Hamsa Yoga")
    # → {"planet": "Jupiter", "condition": "Jupiter in own/exaltation in Kendra"}
    
    # Dasha: what comes after Rahu Mahadasha?
    engine.dasha_sequence("Rahu")
    # → {"next": "Jupiter", "current": 18, "next": 16}
    
    # Panchanga: what is the nature of Pushya nakshatra?
    engine.nakshatra("Pushya")
    # → {"nature": "Light", "lord": "Saturn", ...}
"""

from __future__ import annotations

import json
import os
from typing import Optional


_RULES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "rules.json")


class RuleEngine:
    """Single source of truth for all Vedic rules. Singleton — load once."""

    _instance: Optional["RuleEngine"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def _load(self):
        if self._loaded:
            return
        with open(_RULES_PATH, encoding="utf-8") as f:
            self.rules = json.load(f)
        self._loaded = True
        self._build_indices()

    def __init__(self):
        self._load()

    def _build_indices(self):
        """Pre-build O(1) lookup indices."""
        c = self.rules["categories"]

        # Transit houses: planet -> {good, bad, worst}
        self._transit_houses: dict[str, dict] = {}
        for p in self.rules["constants"]["planets"]:
            pdata = c["transit"]["houses"].get(p, {})
            self._transit_houses[p.lower()] = pdata

        # Vedha: planet -> {house: cancels_house}
        self._vedha: dict[str, dict] = {}
        for p in self.rules["constants"]["planets"]:
            self._vedha[p.lower()] = c["transit"]["vedha"].get(p, {})

        # Moorthi: house_number -> {name, verdict, description}
        self._moorthi: dict[int, dict] = {}
        for k, v in c["transit"]["moorthi"].items():
            self._moorthi[int(k)] = v

        # Tara: count (1-27) -> {name, verdict, description}
        self._tara: dict[int, dict] = {}
        for k, v in c["transit"]["tara"].items():
            self._tara[int(k)] = v

        # Latta: planet -> {distance, direction, effect}
        self._latta: dict[str, dict] = {}
        for p in self.rules["constants"]["planets"]:
            self._latta[p.lower()] = c["transit"]["latta"].get(p, {})

        # Yogas by name
        self._yoga_index: dict[str, dict] = {}
        for cat_name in ["pancha_mahapurusha", "chandra", "raja", "dhana", "nabhasa", "special"]:
            for y in c["yogas"].get(cat_name, []):
                key = y["name"].lower()
                self._yoga_index[key] = y

        # Dasha sequence
        self._dasha_vim: list = c["dasha"]["vimshottari"]["order"]

        # Nakshatra index
        self._nak_index: dict[str, dict] = {}
        for name in self.rules["constants"]["nakshatras"]:
            nature = c["panchanga"]["nak_nature"].get(name, "")
            lord = c["panchanga"].get("nak_lord", {}).get(name, "")
            self._nak_index[name.lower()] = {"name": name, "nature": nature, "lord": lord}

        # Tithi index
        self._tithi_group_names: dict = {}
        if "tithi_group_names" in c["panchanga"]:
            self._tithi_group_names = {int(k): v for k, v in c["panchanga"]["tithi_group_names"].items()}
        self._tithi_groups_raw = c["panchanga"]["tithi_groups"]  # {group_name: [lord, element, desc, verdict]}
        self._dagdha = {int(k): v for k, v in c["panchanga"]["dagdha_by_tithi"].items()}

        # Dignity
        self._exalted = c["dignity"]["exalted"]
        self._debilitated = c["dignity"]["debilitated"]
        self._benefics = c["dignity"]["benefics"]
        self._malefics = c["dignity"]["malefics"]

        # Nitya Yogas
        self._nitya_yogas = c["panchanga"]["nitya_yogas"]

    # ─── Public API ───────────────────────────────────────────────────────

    def transit(self, planet: str, house_from_moon: int) -> dict:
        """Get transit verdict for a planet in a specific house from natal Moon.
        
        Returns {verdict: "good"|"bad"|"worst"|"neutral", type, source}
        """
        data = self._transit_houses.get(planet.lower(), {})
        if house_from_moon in data.get("worst", []):
            return {"verdict": "bad", "type": "worst", "rule": "worst_house"}
        if house_from_moon in data.get("bad", []):
            return {"verdict": "ashubh", "type": "bad", "rule": "bad_house"}
        if house_from_moon in data.get("good", []):
            return {"verdict": "shubh", "type": "good", "rule": "good_house"}
        return {"verdict": "neutral", "type": "neutral", "rule": "no_rule"}

    def vedha_check(self, planet: str, house: int) -> dict:
        """Check if this planet's transit in this house has Vedha cancellation.
        If so, the transit result is cancelled by a planet in the Vedha house."""
        vedha_map = self._vedha.get(planet.lower(), {})
        cancels = vedha_map.get(str(house))
        if cancels is not None:
            return {"vedha": True, "cancels_house": int(cancels), "effect": "Transit result cancelled"}
        return {"vedha": False}

    def moorthi(self, house_from_moon: int) -> dict:
        """Moorthy Nirnaya — quality of transiting Moon from natal Moon."""
        return self._moorthi.get(house_from_moon, {"name": "Unknown", "verdict": "neutral", "description": "Not classified"})

    def tara(self, janma_nak: str, transit_nak: str) -> dict:
        """Tara Balam — count from Janma Nakshatra to transit Moon's nakshatra."""
        naks = self.rules["constants"]["nakshatras"]
        jidx = next((i for i, n in enumerate(naks) if n.lower() == janma_nak.lower()), -1)
        tidx = next((i for i, n in enumerate(naks) if n.lower() == transit_nak.lower()), -1)
        if jidx < 0 or tidx < 0:
            return {"error": "Unknown nakshatra"}
        count = ((tidx - jidx) % 27) + 1
        return self._tara.get(count, {"count": count, "name": "Unknown", "verdict": "neutral", "description": "Not classified"})

    def latta(self, planet: str) -> dict:
        """Latta — does this transiting planet kick the Janma nakshatra?"""
        return self._latta.get(planet.lower(), {})

    def yoga(self, name: str) -> Optional[dict]:
        """Get yoga definition by name. Returns {name, planet, condition, effect, benefic}."""
        return self._yoga_index.get(name.lower())

    def find_yogas(self, planet_positions: dict, lagna_sign: int = 0) -> list[dict]:
        """Find which yoga conditions match the given planet positions.
        planet_positions: {planet_name: sign_index}
        Returns list of matching yoga dicts."""
        matches = []
        for y in self._yoga_index.values():
            if self._check_yoga(y, planet_positions, lagna_sign):
                matches.append(y)
        return matches

    def _check_yoga(self, yoga: dict, positions: dict, lagna: int) -> bool:
        """Simple pattern-matching yoga condition checker."""
        cond = yoga.get("condition", "").lower()
        planet = yoga.get("planet", "").lower()
        if not planet:
            # Multi-planet yoga — check heuristic keywords
            keywords = yoga.get("condition", "").lower()
            for pname, sign in positions.items():
                if pname.lower() in keywords:
                    # Basic checks
                    pass
            return False
        # Single-planet yoga: check if specified planet is in specific condition
        sign = positions.get(planet.title(), positions.get(planet, -1))
        if sign < 0:
            return False
        # Check keywords in condition
        if "exalted" in cond or "exaltation" in cond:
            ex_data = self._exalted.get(planet.title(), {})
            return ex_data.get("sign") == self.rules["constants"]["rashis"][sign]
        if "debilitated" in cond or "debilitation" in cond:
            db_data = self._debilitated.get(planet.title(), {})
            return db_data.get("sign") == self.rules["constants"]["rashis"][sign]
        if "kendra" in cond:
            kendra_from_lagna = {1, 4, 7, 10}
            house_from_lagna = ((sign - lagna) % 12) + 1
            return house_from_lagna in kendra_from_lagna
        if "kona" in cond or "trine" in cond:
            trikona_from_lagna = {1, 5, 9}
            house_from_lagna = ((sign - lagna) % 12) + 1
            return house_from_lagna in trikona_from_lagna
        return False

    def dasha_sequence(self, planet: str) -> dict:
        """Get dasha order info. Returns {index, next_planet, duration_years}."""
        order = self._dasha_vim
        periods = self.rules["categories"]["dasha"]["vimshottari"]["periods"]
        planet_title = planet.title()
        try:
            idx = order.index(planet_title)
        except ValueError:
            return {"error": f"Unknown dasha planet: {planet}"}
        next_idx = (idx + 1) % len(order)
        return {
            "index": idx, "planet": order[idx],
            "next_planet": order[next_idx],
            "duration_years": periods.get(order[idx], 0),
            "next_duration_years": periods.get(order[next_idx], 0),
        }

    def nakshatra(self, name: str) -> Optional[dict]:
        """Get nakshatra details (nature, lord, etc.)."""
        return self._nak_index.get(name.lower())

    def tithi_group(self, tithi_num: int) -> dict:
        """Get Tithi group info (Nanda, Bhadra, Jaya, Rikta, Purna) with lords and elements."""
        tip = ((tithi_num - 1) % 15) + 1 if tithi_num > 15 else tithi_num
        group_num = ((tip - 1) % 5) + 1
        group_name = self._tithi_group_names.get(group_num, "Unknown")
        group_info = self._tithi_groups_raw.get(group_name, ["?", "?", "?", "?"])
        return {
            "group": group_name,
            "tip": tip,
            "lord": group_info[0],
            "element": group_info[1],
            "description": group_info[2],
            "verdict": group_info[3],
            "dagdha_rasis": self._dagdha.get(tip, []),
        }

    def dignity(self, planet: str, sign: str, degree: float) -> dict:
        """Check a planet's dignity: exalted, debilitated, own sign, or neutral."""
        p = planet.title()
        ex = self._exalted.get(p, {})
        db = self._debilitated.get(p, {})
        if ex.get("sign") == sign:
            return {"status": "exalted", "source": "BPHS"}
        if db.get("sign") == sign:
            return {"status": "debilitated", "source": "BPHS"}
        from vedic_engine.rules.transit_rules import OWN_SIGN
        if sign in OWN_SIGN.get(p, []):
            return {"status": "own_sign", "source": "BPHS"}
        if p in self._benefics:
            return {"status": "benefic", "source": "BPHS"}
        if p in self._malefics:
            return {"status": "malefic", "source": "BPHS"}
        return {"status": "neutral", "source": "BPHS"}

    # ─── Stats ────────────────────────────────────────────────────────────

    def predict_synthesis(self, positions: dict, query: dict) -> dict:
        """Run a complete rule-based synthesis for a query.
        
        Args:
            positions: {planet: {rashi, longitude, nakshatra, ...}}
            query: {date, time, janma_rashi, janma_nakshatra, natal_sign, ...}
        
        Returns a structured prediction with rule citations.
        """
        result = {"verdict": "neutral", "score": 0, "factors": [], "warnings": []}

        # 1. Transit analysis
        janma_rashi = query.get("janma_rashi", "")
        janma_nak = query.get("janma_nakshatra", "")
        natal_sign = query.get("natal_sign", {})

        if janma_rashi:
            jr_idx = self.rules["constants"]["rashis"].index(janma_rashi) if janma_rashi in self.rules["constants"]["rashis"] else -1
            if jr_idx >= 0:
                for p, data in positions.items():
                    if p in ("Rahu", "Ketu"):
                        continue
                    p_rashi = data.get("rashi", "")
                    p_idx = self.rules["constants"]["rashis"].index(p_rashi) if p_rashi in self.rules["constants"]["rashis"] else -1
                    if p_idx < 0:
                        continue
                    house = ((p_idx - jr_idx) % 12) + 1
                    verdict = self.transit(p, house)
                    if verdict["verdict"] == "shubh":
                        result["score"] += 3
                        result["factors"].append(f"{p} in {house}th from Moon → favourable transit")
                    elif verdict["verdict"] == "ashubh":
                        result["score"] -= 3
                        result["factors"].append(f"{p} in {house}th from Moon → unfavourable transit")
                        if verdict.get("type") == "worst":
                            result["warnings"].append(f"{p} in {house}th from Moon is the worst transit position")

        # 2. Moorthy
        if janma_rashi and "Moon" in positions:
            moon_rashi = positions["Moon"].get("rashi", "")
            m_idx = self.rules["constants"]["rashis"].index(moon_rashi) if moon_rashi in self.rules["constants"]["rashis"] else -1
            j_idx = self.rules["constants"]["rashis"].index(janma_rashi) if janma_rashi in self.rules["constants"]["rashis"] else -1
            if m_idx >= 0 and j_idx >= 0:
                m_house = ((m_idx - j_idx) % 12) + 1
                mo = self.moorthi(m_house)
                result["factors"].append(f"Moon in {m_house}th from Janma Rashi → {mo['name']} ({mo['verdict']})")
                if mo["verdict"] == "ashubh":
                    result["score"] -= 2

        # 3. Tara Balam
        if janma_nak and "Moon" in positions:
            moon_nak = positions["Moon"].get("nakshatra", "")
            t = self.tara(janma_nak, moon_nak)
            result["factors"].append(f"Tara Balam: {janma_nak} → {moon_nak} = {t.get('name', '?')} ({t.get('verdict', '?')})")
            if t.get("verdict") == "ashubh":
                result["score"] -= 3

        # 4. Yoga detection
        if natal_sign:
            yogas = self.find_yogas(natal_sign, natal_sign.get("Lagna", 0))
            for y in yogas[:10]:
                result["factors"].append(f"Yoga: {y['name']} {'(benefic)' if y.get('benefic') else '(challenging)'}")
                if y.get("benefic"):
                    result["score"] += 4
                else:
                    result["score"] -= 2

        # 5. Dasha context
        dasha_info = query.get("dasha", {})
        if dasha_info:
            maha = dasha_info.get("mahadasha", "")
            if maha:
                ds = self.dasha_sequence(maha)
                result["factors"].append(f"Running {maha} Mahadasha ({ds.get('duration_years', '?')} years)")

        # Final verdict
        if result["score"] >= 12:
            result["verdict"] = "Highly Auspicious"
        elif result["score"] >= 6:
            result["verdict"] = "Favourable"
        elif result["score"] >= 0:
            result["verdict"] = "Mixed"
        elif result["score"] >= -6:
            result["verdict"] = "Caution"
        else:
            result["verdict"] = "Inauspicious"

        return result
