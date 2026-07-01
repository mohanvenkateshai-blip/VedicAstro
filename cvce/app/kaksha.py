"""Kaksha calendar and current position (8 per sign, standard BPHS sequence)."""

from __future__ import annotations

from datetime import date

from app.ephem import PLANET_NAMES, RASHIS
from knowledge_engine.integration import get_knowledge_engine, get_structured_book

# Standard Kaksha lords sequence (8 per sign)
KAKSHA_SEQUENCE = [
    "Saturn",
    "Jupiter",
    "Mars",
    "Sun",
    "Venus",
    "Mercury",
    "Moon",
    "Lagna",
]
_KAKSHA_SPAN = 30.0 / 8.0  # 3°45′

# Graph/structured sources for Kaksha (bindu, ashtakavarga)
_GRAPH_KAKSHA_IDS = [
    "phaladeepika_concept_bindu",
    "phaladeepika_concept_sarvashtakavarga",
    "gyan_ashtakavarga_system_comprehensive_handbo_corpus",
]

_kaksha_cache: dict = {"version": None, "citations": [], "structured": {}}


def _on_kaksha_refresh(new_version: str) -> None:
    """KE on_refresh: reload structured + graph citations for Kaksha."""
    global _kaksha_cache
    _kaksha_cache = {"version": new_version, "citations": [], "structured": {}}
    try:
        ke = get_knowledge_engine()
        for nid in _GRAPH_KAKSHA_IDS:
            node = ke.get_safe_node(nid) if hasattr(ke, "get_safe_node") else None
            if node:
                _kaksha_cache["citations"].append(
                    {
                        "id": nid,
                        "label": node.get("label", nid),
                        "description": (node.get("description") or "")[:300],
                    }
                )
        # Load any structured Ashtakavarga/Kaksha book
        for bid in ["phaladeepika", "gyan_ashtakavarga_system_comprehensive_handbo_corpus"]:
            try:
                b = get_structured_book(bid)
                if b:
                    _kaksha_cache["structured"][bid] = {
                        "chapters": len(b.get("chapters", [])),
                        "source": bid,
                    }
            except Exception:
                pass
    except Exception:
        pass


def _register_kaksha_engine() -> None:
    try:
        ke = get_knowledge_engine()
        ke.register_engine("kaksha", on_refresh=_on_kaksha_refresh)
    except Exception:
        pass


_register_kaksha_engine()


def _kaksha_index(deg_in_sign: float) -> int:
    return min(7, max(0, int(deg_in_sign / _KAKSHA_SPAN)))


def get_kaksha_calendar_for_sign(sign_idx: int, prastara: list | None = None) -> list[dict]:
    """Full 8-kaksha calendar row for one sign."""
    cal = []
    for i, lord in enumerate(KAKSHA_SEQUENCE):
        lo = i * _KAKSHA_SPAN
        hi = (i + 1) * _KAKSHA_SPAN
        bindu = False
        if prastara is not None:
            try:
                op = {
                    "Sun": 0,
                    "Moon": 1,
                    "Mars": 2,
                    "Mercury": 3,
                    "Jupiter": 4,
                    "Venus": 5,
                    "Saturn": 6,
                    "Lagna": 7,
                }.get(lord)
                if op is not None:
                    bindu = bool(prastara[op][sign_idx]) if len(prastara) > op else False
            except Exception:
                pass
        cal.append(
            {
                "index": i + 1,
                "lord": lord,
                "rangeDeg": f"{lo:.2f}–{hi:.2f}",
                "binduActive": bindu,
                "sign": RASHIS[sign_idx],
            }
        )
    return cal


def get_current_kaksha(planet: str, lon: float, sign_idx: int, prastara=None) -> dict:
    deg = lon % 30.0
    idx = _kaksha_index(deg)
    lord = KAKSHA_SEQUENCE[idx]
    bindu = False
    if prastara is not None:
        try:
            op = {
                "Sun": 0,
                "Moon": 1,
                "Mars": 2,
                "Mercury": 3,
                "Jupiter": 4,
                "Venus": 5,
                "Saturn": 6,
                "Lagna": 7,
            }.get(lord)
            if op is not None:
                bindu = bool(prastara[op][sign_idx])
        except Exception:
            pass
    return {
        "planet": planet,
        "sign": RASHIS[sign_idx],
        "degreeInSign": round(deg, 2),
        "kakshaIndex": idx + 1,
        "kakshaLord": lord,
        "binduActive": bindu,
    }


def kaksha_calendar_full(prastara: list | None = None) -> dict:
    """Complete 12×8 Kaksha calendar + source notes."""
    signs = {}
    for si in range(12):
        signs[RASHIS[si]] = get_kaksha_calendar_for_sign(si, prastara)
    return {
        "calendar": signs,
        "sequence": KAKSHA_SEQUENCE,
        "spanDeg": _KAKSHA_SPAN,
        "ke_version": _kaksha_cache.get("version"),
        "source_notes": _kaksha_cache.get("citations", []),
        "structured_books": _kaksha_cache.get("structured", {}),
    }
