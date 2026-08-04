"""
GraphRAG muhurta rules provider — load vara/tithi yoga rules from graph.json.
"""

from __future__ import annotations

import os

from .graph import GraphRAG


def graph_muhurta_enabled() -> bool:
    raw = os.environ.get("CVCE_GRAPH_AS_MUHURTA", "1")
    return raw.strip().lower() in ("1", "true", "yes", "on")


class GraphMuhurtaRules:
    _instance: GraphMuhurtaRules | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._built = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_built", False):
            return
        self.graph = GraphRAG()
        muhurta_src_hints = (
            "muhurta",
            "tara_balam",
            "do_ghati",
            "celestial",
            "vara_tithi",
            "tithi–vara",
            "tithi vara",
            "classical_muhurta",
            "yoga handbook",
            "muhurta_yogas",
        )
        def _is_muhurta_src(n: dict) -> bool:
            sf = (n.get("source_file") or "").lower()
            nid = (n.get("id") or "").lower()
            return any(h in sf or h in nid for h in muhurta_src_hints)
        self._yoga_nodes = [
            n
            for n in self.graph.nodes
            if n.get("is_muhurta_yoga")
            or "muhurta_yoga" in n.get("id", "")
            or ((n.get("nature") or n.get("verdict")) and _is_muhurta_src(n))
        ]
        self._combo_nodes = [
            n
            for n in self.graph.nodes
            if n.get("vara_lord") and (n.get("tithi_group") or n.get("tithi_num"))
        ]
        self._sav_bands = [
            n
            for n in self.graph.nodes
            if n.get("domain") == "ashtakavarga" or "sav_band" in n.get("id", "")
        ]
        self._built = True

    def yoga_hits(self, vara_lord: str, tithi_group: str, tithi_tip: int) -> list[dict]:
        hits: list[dict] = []
        for n in self._combo_nodes:
            if n.get("vara_lord") != vara_lord:
                continue
            tg = n.get("tithi_group")
            tn = n.get("tithi_num")
            if tg and tg == tithi_group:
                hits.append(
                    {
                        "name": n.get("label", "").split(":")[0].strip(),
                        "nature": n.get("verdict", n.get("nature", "mixed")),
                        "source": n.get("source_file", "graph.json"),
                        "detail": n.get("label", ""),
                    }
                )
            elif tn and int(tn) == tithi_tip:
                hits.append(
                    {
                        "name": n.get("label", "").split(":")[0].strip(),
                        "nature": n.get("verdict", n.get("nature", "mixed")),
                        "source": n.get("source_file", "graph.json"),
                        "detail": n.get("label", ""),
                    }
                )
        # Expanded extraction: pull explicit yogas from additional nodes/labels
        # (Celestial Alignments, Tithi–Vāra, Tara Balam, muhurta handbooks, etc.)
        # These add provenance/citations even when structured vara/tithi attrs are absent.
        seen = {(h.get("name"), h.get("detail")) for h in hits}
        name_nature_seen = {(h.get("name"), h.get("nature")) for h in hits}
        for n in getattr(self, "_yoga_nodes", []):
            nat = n.get("verdict") or n.get("nature")
            if not nat:
                continue
            # skip ones already covered via combo path
            if n.get("vara_lord") and (n.get("tithi_group") or n.get("tithi_num")):
                continue
            raw_name = (n.get("label", "") or "").split(":")[0].strip() or "Yoga"
            name = raw_name
            # Safe truncation repairs: only target leading fragments or whole-token short forms.
            # Avoid naive infix replace on already-correct words like "Dagdha".
            def _repair(y: str) -> str:
                y = y.replace("auAuspicious", "Auspicious")
                y = y.replace("AuAuspicious", "Auspicious")
                y = y.replace("spicious Vara + Tithi Yoga", "Auspicious Vara + Tithi Yoga")
                y = y.replace("spicious_varatithi", "Auspicious Vara Tithi")
                y = y.replace("DaDagdha", "Dagdha")
                low = y.lower()
                # leading fragment fixes (id-norm often drops first letters)
                if low.startswith("ddha"): y = "Dagdha" + y[4:]
                elif low.startswith("gdha"): y = "Dagdha" + y[4:]
                elif low.startswith("rita"): y = "Amrita" + y[4:]
                elif low.startswith("akacha"): y = "Krakacha" + y[6:]
                elif low.startswith("tasana"): y = "Hutasana" + y[6:]
                elif low.startswith("hurta"): y = "Muhurta" + y[5:]
                if "uspicious" in y.lower() and "Auspicious" not in y:
                    y = y.replace("uspicious", "Auspicious").replace("Uspicious", "Auspicious")
                # remove stray leading "au" fragments
                if y.lower().startswith("au") and len(y) > 2 and not y.lower().startswith("ausp"):
                    y = y[2:]
                return y
            name = _repair(name)
            # last resort short token
            if len(name) <= 7:
                low = name.lower()
                if low.endswith("ddha") or low == "ddha": name = "Dagdha"
                elif low.endswith("rita") or low == "rita": name = "Amrita"
                elif low.endswith("akacha") or low == "akacha": name = "Krakacha"
            key = (name, n.get("label", ""))
            nnk = (name, nat)
            if key in seen or nnk in name_nature_seen:
                continue
            hits.append(
                {
                    "name": name,
                    "nature": nat,
                    "source": n.get("source_file", "graph.json"),
                    "detail": n.get("definition") or n.get("label", ""),
                }
            )
            seen.add(key)
            name_nature_seen.add(nnk)
        return hits

    def sav_band_for_bindus(self, bindus: int) -> dict | None:
        for n in self._sav_bands:
            lo = n.get("min_bindus")
            hi = n.get("max_bindus")
            if lo is None:
                continue
            hi = hi if hi is not None else 999
            if lo <= bindus <= hi:
                return {
                    "band": n.get("label"),
                    "verdict": n.get("verdict", "neutral"),
                    "source": n.get("source_file", "graph.json"),
                }
        return None


def active_muhurta_rules() -> GraphMuhurtaRules | None:
    if not graph_muhurta_enabled():
        return None
    try:
        return GraphMuhurtaRules()
    except Exception:
        return None
