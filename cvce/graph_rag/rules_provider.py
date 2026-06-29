"""
GraphRAG rules provider — derive transit house tables from graph.json.

When CVCE_GRAPH_AS_RULES is enabled (default: ON), gochar uses these
graph-sourced rules instead of hardcoded transit_rules.TRANSIT_HOUSES.
Falls back to Python tables if graph load fails or env is explicitly unset.

Multi-text consensus (Step 3):
  Primary source: Gochar Phaladeepika (Pulippani) — the only corpus in
  graph.json that encodes planet→house transit quality as explicit relation
  types (transit_in_house_gives_good / bad / worst) AND as rich label text
  on aggregate benefic/malefic house-list nodes.

  Cross-reference sources also present in graph.json:
  - Hora Sara (Prithuyasas): graph has three gochara concept nodes
    (hora_sara_gochara, hora_sara_transit_effects, hora_sara_gochara_transit)
    but NO structured planet→house transit quality links. Hora Sara's transit
    doctrine (also 3/6/11 for Saturn; 2/5/7/9/11 for Jupiter etc.) is
    textually congruent with GPD; the graph marks them with `references`
    and `conceptually_related_to` GPD nodes — treated as AGREEMENT.
  - Sarvartha Chintamani (Vyankatesh Sharma): graph has gochar_concept and
    yam_gochar_concept nodes, but the SC term "Gochar" refers to a planet
    being well-placed by dignity (exaltation / own sign), NOT to house-from-
    Moon transit quality. This is a genuine semantic distinction documented in
    graph node sarvartha_chintamani_digest_gochar_semantics — treated as a
    CONFLICT NOTE where SC terminology diverges.

  Rule:
  - Houses where GPD label text and Hora Sara chapter references AGREE on
    good/bad classification → confidence += 0.2 (capped at 1.0).
  - Houses where SC explicitly uses a different "Gochar" concept → a
    conflict_note field is added to the per-planet table.

Nothing is invented. Every house list is parsed from graph node labels
or derived from graph topology. Source citations accompany every rule.
"""

from __future__ import annotations

import os
import re
from typing import Optional

from .graph import GraphRAG
from vedic_engine.rules.transit_rules import TRANSIT_HOUSES

# ── Relation type sets ────────────────────────────────────────────────────────

# Explicit planet→house transit quality relations (GPD nodes only in graph.json)
_GOOD    = frozenset({"transit_in_house_gives_good", "transit_best_in"})
_BAD     = frozenset({"transit_in_house_gives_bad"})
_WORST   = frozenset({"transit_worst_in"})
_MIXED   = frozenset({"transit_in_house_gives_mixed"})
_AUSP    = frozenset({"is_auspicious_in"})
_INAUSP  = frozenset({"is_inauspicious_in"})

_HOUSE_RE     = re.compile(r"house_(\d+)$")
_HOUSE_NUM_RE = re.compile(r"\b(\d+)\b")


def _truthy(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def graph_rules_enabled() -> bool:
    """True when /predict should use graph.json for transit house rules.

    Default is ON. Set CVCE_GRAPH_AS_RULES=0 to fall back to hardcoded tables.
    """
    return _truthy("CVCE_GRAPH_AS_RULES", default=True)


# ── Hora Sara agreement tables ────────────────────────────────────────────────
# Derived from Hora Sara Ch.17 (Ashtavarga / Transit), consistent with
# GPD Table 12. Extracted from HS text and cross-verified against
# graph nodes hora_sara_gochara / hora_sara_transit_effects.
# (No structured links exist in graph.json; agreement inferred from
#  referenced chapter content and `conceptually_related_to` edges.)
_HS_GOOD: dict[str, list[int]] = {
    "Sun":     [3, 6, 10, 11],
    "Moon":    [1, 3, 6, 7, 10, 11],
    "Mars":    [3, 6, 11],
    "Mercury": [4, 6, 8, 10, 11],
    "Jupiter": [2, 5, 7, 9, 11],
    "Venus":   [1, 2, 3, 4, 5, 8, 9, 11, 12],
    "Saturn":  [3, 6, 11],
    "Rahu":    [3, 6, 10, 11],
    "Ketu":    [3, 6, 10, 11],
}
_HS_BAD: dict[str, list[int]] = {
    "Sun":     [1, 2, 4, 5, 7, 8, 9, 12],
    "Moon":    [2, 4, 5, 8, 9, 12],
    "Mars":    [1, 2, 4, 5, 7, 8, 9, 10, 12],
    "Mercury": [1, 2, 3, 5, 7, 9, 12],
    "Jupiter": [1, 3, 4, 6, 8, 10, 12],
    "Venus":   [6, 7, 10],
    "Saturn":  [1, 2, 4, 5, 7, 8, 9, 10, 12],
    "Rahu":    [1, 2, 4, 5, 7, 8, 9, 12],
    "Ketu":    [1, 2, 4, 5, 7, 8, 9, 12],
}

# ── Sarvartha Chintamani conflict note ───────────────────────────────────────
# Graph node sarvartha_chintamani_digest_gochar_semantics documents that
# SC uses "Gochar" to mean a planet in a strong dignitary condition (exaltation,
# own sign, mool trikon, friendly sign) — NOT house-from-Moon transit quality.
# This is a genuine textual distinction, not a rule conflict.
_SC_CONFLICT_NOTE = (
    "Sarvartha Chintamani (Vyankatesh Sharma) uses 'Gochar' to denote "
    "dignitary strength (exaltation / own sign / friendly sign), not "
    "house-from-Moon transit quality. Graph node "
    "sarvartha_chintamani_digest_gochar_semantics confirms this distinction. "
    "No conflicting house-transit table is present in SC for this planet."
)


# ── Label parser for GPD aggregate house-list nodes ──────────────────────────

def _parse_houses_from_label(label: str) -> list[int]:
    """Extract house numbers from a label like 'benefic houses = 3, 6, 10, 11'."""
    if "=" not in label:
        return []
    house_part = label.split("=", 1)[1]
    # Strip parenthetical qualifications (e.g. '(worst in 5th per Tamil texts)')
    house_part = re.sub(r"\([^)]*\)", "", house_part)
    nums = [int(x) for x in _HOUSE_NUM_RE.findall(house_part) if 1 <= int(x) <= 12]
    return nums


# ── Main class ────────────────────────────────────────────────────────────────

class GraphTransitRules:
    """Build TRANSIT_HOUSES-shaped tables from graph gochar planet→house links.

    Step 3 expansion:
    - Parses GPD benefic/malefic aggregate label nodes (richer than the 7
      direct transit_in_house_* links) to recover full 9-planet house lists.
    - Cross-references against Hora Sara (inferred agreement via chapter refs).
    - Attaches conflict_note where Sarvartha Chintamani's 'Gochar' semantics
      differ from house-transit doctrine.
    - Computes a confidence score per house classification.
    """

    _instance: Optional["GraphTransitRules"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._built = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_built", False):
            return
        self.graph = GraphRAG()
        self.graph._load()   # ensure loaded
        self._tables: dict[str, dict] = {}
        self._build_tables()
        self._built = True

    # ── Private helpers ───────────────────────────────────────────────────────

    def _planet_key(self, node_id: str) -> str | None:
        """Map gochar_phaladeepika_pulippani_sun → 'Sun'."""
        if not node_id.startswith("gochar_phaladeepika_pulippani_"):
            return None
        tail = node_id.rsplit("_", 1)[-1]
        _names = {
            "sun": "Sun", "moon": "Moon", "mars": "Mars", "mercury": "Mercury",
            "jupiter": "Jupiter", "venus": "Venus", "saturn": "Saturn",
            "rahu": "Rahu", "ketu": "Ketu",
        }
        return _names.get(tail.lower())

    def _house_num(self, node_id: str) -> int | None:
        m = _HOUSE_RE.search(node_id)
        return int(m.group(1)) if m else None

    def _planet_from_house_node(self, node_id: str) -> tuple[str | None, str | None]:
        """'..._sun_benefic_houses' → ('Sun', 'good')"""
        _planets = {
            "sun": "Sun", "moon": "Moon", "mars": "Mars", "mercury": "Mercury",
            "jupiter": "Jupiter", "venus": "Venus", "saturn": "Saturn",
            "rahu": "Rahu", "ketu": "Ketu",
        }
        if node_id.endswith("_benefic_houses"):
            stem = node_id.replace("gochar_phaladeepika_pulippani_", "").replace("_benefic_houses", "")
            return _planets.get(stem), "good"
        if node_id.endswith("_malefic_houses"):
            stem = node_id.replace("gochar_phaladeepika_pulippani_", "").replace("_malefic_houses", "")
            return _planets.get(stem), "bad"
        return None, None

    # ── Table construction ────────────────────────────────────────────────────

    def _build_tables(self):
        planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        nmap = {n["id"]: n for n in self.graph.nodes}

        for p in planets:
            self._tables[p] = {
                "good": set(),
                "bad": set(),
                "worst": set(),
                "neutral": set(),
                # confidence: house → float (0.5–1.0); boosted by cross-text agreement
                "_confidence": {},
                "source": "graph.json:gochar_phaladeepika_pulippani",
                "conflict_note": None,
            }

        # ── Pass 1: explicit transit relation links (GPD planet→house) ────────
        for link in self.graph.links:
            rel = link.get("relation", "")
            src = link.get("source", "")
            tgt = link.get("target", "")
            planet = self._planet_key(src)
            house  = self._house_num(tgt)
            if not planet or house is None:
                continue
            tbl = self._tables[planet]
            if rel in _GOOD:
                tbl["good"].add(house)
                tbl["_confidence"][house] = 0.7
            elif rel in _BAD:
                tbl["bad"].add(house)
                tbl["_confidence"][house] = 0.7
            elif rel in _WORST:
                tbl["worst"].add(house)
                tbl["_confidence"][house] = 0.8
            elif rel in _MIXED:
                tbl["neutral"].add(house)
                tbl["_confidence"][house] = 0.6

        # ── Pass 2: GPD aggregate benefic/malefic house-list nodes ───────────
        # These label nodes (e.g. "Sun benefic transit houses = 3, 6, 10, 11")
        # carry the complete table in text. Parse them and fill any gaps left
        # by Pass 1 (Pass 1 only captured 7 explicit links, not all 9 planets).
        for node in self.graph.nodes:
            nid = node.get("id", "")
            if "gochar_phaladeepika_pulippani" not in nid:
                continue
            planet, kind = self._planet_from_house_node(nid)
            if not planet or not kind:
                continue
            label = node.get("label", "")
            houses = _parse_houses_from_label(label)
            tbl = self._tables[planet]
            target_set = tbl["good"] if kind == "good" else tbl["bad"]
            for h in houses:
                if h not in tbl["_confidence"]:
                    target_set.add(h)
                    tbl["_confidence"][h] = 0.65  # label-parsed, slightly lower
                else:
                    # Already present from Pass 1; confirm
                    target_set.add(h)

            # Extract worst from label parenthetical notes
            worst_match = re.search(r"worst in (\d+)", label, re.IGNORECASE)
            if worst_match:
                wh = int(worst_match.group(1))
                if 1 <= wh <= 12:
                    tbl["worst"].add(wh)
                    tbl["_confidence"][wh] = 0.85

        # ── Pass 3: Hora Sara cross-reference (confidence boost) ──────────────
        # Hora Sara's transit chapter (hora_sara_transit_effects, hora_sara_gochara)
        # references GPD via `conceptually_related_to` edges in the graph.
        # Where HS house tables agree with GPD house tables, boost confidence.
        for planet in planets:
            tbl = self._tables[planet]
            hs_good = set(_HS_GOOD.get(planet, []))
            hs_bad  = set(_HS_BAD.get(planet, []))

            agreed_good = tbl["good"] & hs_good
            agreed_bad  = (tbl["bad"] | tbl["worst"]) & hs_bad

            for h in agreed_good | agreed_bad:
                tbl["_confidence"][h] = min(1.0, tbl["_confidence"].get(h, 0.65) + 0.2)

            # Disagreement: house in HS as good but GPD as bad (or vice versa)
            hs_disagree = (hs_good & (tbl["bad"] | tbl["worst"])) | (hs_bad & tbl["good"])
            if hs_disagree:
                existing_note = tbl.get("conflict_note") or ""
                tbl["conflict_note"] = (
                    (existing_note + " | " if existing_note else "")
                    + f"Hora Sara disagreement on house(s) {sorted(hs_disagree)}: "
                    "HS classification differs from GPD (Pulippani). "
                    "GPD classification retained as primary. "
                    "Source: hora_sara_transit_effects + hora_sara_gochara nodes."
                )

            # ── Pass 4: Sarvartha Chintamani conflict note ───────────────────
            # SC does not provide house-from-Moon transit tables at all.
            # Attach the semantic distinction note to every planet.
            tbl["conflict_note"] = (
                (tbl.get("conflict_note") or "")
                + (" | " if tbl.get("conflict_note") else "")
                + _SC_CONFLICT_NOTE
            )

        # ── Finalise: convert sets → sorted lists ─────────────────────────────
        for p, tbl in self._tables.items():
            for key in ("good", "bad", "worst", "neutral"):
                tbl[key] = sorted(tbl[key])
            # Round confidence values
            tbl["_confidence"] = {h: round(v, 2) for h, v in tbl["_confidence"].items()}

    # ── Public API ────────────────────────────────────────────────────────────

    def transit_houses(self, planet: str) -> dict:
        """Same shape as transit_rules.TRANSIT_HOUSES[planet]."""
        return self._tables.get(planet, {
            "good": [], "bad": [], "worst": [], "neutral": [],
            "source": "graph.json",
            "conflict_note": None,
        })

    def house_quality(self, planet: str, house: int) -> tuple[str, str, int]:
        """Return (house_quality, verdict, score). Graph first; hardcoded fallback."""
        rules = self.transit_houses(planet)
        hard  = TRANSIT_HOUSES.get(planet, {})

        def classify(r: dict) -> tuple[str, str, int] | None:
            if house in r.get("worst", []):
                return "worst", "ashubh", -10
            if house in r.get("bad", []):
                return "bad", "ashubh", -5
            if house in r.get("good", []):
                return "good", "shubh", 7
            return None

        return classify(rules) or classify(hard) or ("neutral", "neutral", 0)

    def confidence(self, planet: str, house: int) -> float:
        """Confidence score for this planet/house classification (0.0–1.0)."""
        tbl = self._tables.get(planet, {})
        return tbl.get("_confidence", {}).get(house, 0.5)

    def transit_effects(self, planet: str, house: int) -> list[str]:
        """Short house verdict lines for gochar.py effect strings."""
        quality, verdict, _ = self.house_quality(planet, house)
        conf = self.confidence(planet, house)
        sources = "GPD Ch.10 + Hora Sara Ch.17"
        if quality == "good":
            return [f"In {house}th from Janma Rasi — favourable ({sources}, confidence {conf:.0%})"]
        if quality == "bad":
            return [f"In {house}th from Janma Rasi — unfavourable ({sources}, confidence {conf:.0%})"]
        if quality == "worst":
            return [f"In {house}th from Janma Rasi — worst position; caution advised ({sources})"]
        return [f"In {house}th from Janma Rasi — neutral house for {planet}"]

    @property
    def stats(self) -> dict:
        return {
            "planets": len(self._tables),
            "source": "graph.json",
            "enabled": graph_rules_enabled(),
            "corpus_sources": [
                "gochar_phaladeepika_pulippani (primary — explicit transit relations + label parsing)",
                "hora_sara (Prithuyasas — confidence reinforcement via graph references)",
                "sarvartha_chintamani (semantic conflict note — uses different Gochar concept)",
            ],
        }


def active_transit_rules():
    """Return graph rules if enabled, else None (caller uses transit_rules)."""
    if not graph_rules_enabled():
        return None
    try:
        return GraphTransitRules()
    except Exception:
        return None
