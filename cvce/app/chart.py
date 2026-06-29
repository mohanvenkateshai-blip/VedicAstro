"""
Canonical `chart_data` composition.

`build_chart_geometry` produces the deterministic, chart-shaped core of a
horoscope — ascendant, the nine bodies, natal sign map, divisional charts
(Shodashvarga) and Ashtakavarga (BAV + SAV). `server.py` layers the
time-dependent blocks (dasha, shadbala, yogas, panchanga-at-birth) on top to
form the full canonical payload that the portal's Muhurta sub-module consumes.

This module is the contract surface — its output shape must stay in lockstep
with `docs/chart_data.schema.json`.
"""

from __future__ import annotations

from jhora import utils
from jhora.horoscope.chart import ashtakavarga, charts

from .ephem import PLANET_NAMES, ascendant, positions, set_ayanamsa

# Map PyJHora planet ids / the ascendant symbol to our canonical names.
_PID_TO_NAME = {i: n for i, n in enumerate(PLANET_NAMES)}
_LAGNA = "Lagna"

# Human labels for the divisional charts we expose.
VARGA_NAMES = {
    1: "Rasi",
    2: "Hora",
    3: "Drekkana",
    4: "Chaturthamsa",
    7: "Saptamsa",
    9: "Navamsa",
    10: "Dasamsa",
    12: "Dwadasamsa",
    16: "Shodasamsa",
    24: "Chaturvimsamsa",
    30: "Trimsamsa",
    60: "Shashtiamsa",
}


def _varga_sign_map(jd: float, place, dcf: int) -> dict:
    """Return {planet|'Lagna': signIndex} for a divisional chart factor `dcf`.

    PyJHora `divisional_chart` returns [[planet,(raasi, deg_in_sign)], ...]
    where planet is an int pid or the ascendant symbol 'L'.
    """
    pp = charts.divisional_chart(jd, place, divisional_chart_factor=dcf)
    out = {}
    for planet, (raasi, _deg) in pp:
        if isinstance(planet, str):  # 'L' ascendant symbol
            out[_LAGNA] = int(raasi)
        else:
            name = _PID_TO_NAME.get(int(planet))
            if name:
                out[name] = int(raasi)
    return out, pp


def _ashtakavarga(d1_planet_positions) -> dict:
    """Bhinna (per-contributor) + Sarva ashtakavarga from the D1 chart.

    Returns sav[12], bav{Sun..Saturn,Lagna:[12]}, and lagnaSignIdx.
    """
    h2p = utils.get_house_planet_list_from_planet_positions(d1_planet_positions)
    binna, samudhaya, _prastara = ashtakavarga.get_ashtaka_varga(h2p)
    # binna rows: 0..6 = Sun..Saturn, 7 = Lagna
    bav_labels = PLANET_NAMES[:7] + [_LAGNA]
    bav = {bav_labels[i]: [int(x) for x in binna[i]] for i in range(len(bav_labels))}
    # lagna sign index from the house→planet list
    lagna_sign = None
    for sign_idx, occupants in enumerate(h2p):
        if "L" in str(occupants).split("/"):
            lagna_sign = sign_idx
            break
    return {
        "sav": [int(x) for x in samudhaya],
        "bav": bav,
        "lagnaSignIdx": lagna_sign,
    }


def build_chart_geometry(jd: float, place, ayanamsa: str, vargas: list[int]) -> dict:
    """Deterministic chart core. `place` is a PyJHora Place; `jd` local-civil JD."""
    set_ayanamsa(ayanamsa)

    asc = ascendant(jd, place)
    bodies = positions(jd, place)
    natal_sign = {b["planet"]: b["signIndex"] for b in bodies}

    # Divisional charts. D1 doubles as the source for natalSign + ashtakavarga.
    varga_charts = {}
    d1_pp = None
    for dcf in sorted(set(vargas) | {1}):
        sign_map, pp = _varga_sign_map(jd, place, dcf)
        if dcf == 1:
            d1_pp = pp
        if dcf in vargas:
            varga_charts[f"D{dcf}"] = {"name": VARGA_NAMES.get(dcf, f"D{dcf}"), "signs": sign_map}

    akv = _ashtakavarga(d1_pp) if d1_pp is not None else None

    return {
        "ayanamsa": ayanamsa,
        "jd": jd,
        "ascendant": asc,
        "lagna": {
            "rashi": asc["rashi"],
            "signIndex": asc["signIndex"],
            "nakshatra": asc["nakshatra"],
            "pada": asc["pada"],
            "degInSign": asc["degInSign"],
            "degLabel": asc["degLabel"],
        },
        "planets": bodies,
        "natalSign": natal_sign,
        "vargas": varga_charts,
        "ashtakavarga": akv,
        "pushkarNavamsha": _pushkar_navamsha(bodies),
    }


# Pushkar Navamsha degrees (auspicious positions in D9)
# Each rashi has 2 Pushkar degrees — table from BPHS / Sarvartha Chintamani
_PUSHKAR_DEGREES = {
    0: [21, 27],  # Aries
    1: [3, 15],  # Taurus
    2: [9, 21],  # Gemini
    3: [13, 27],  # Cancer
    4: [15, 23],  # Leo
    5: [17, 23],  # Virgo
    6: [19, 27],  # Libra
    7: [14, 24],  # Scorpio
    8: [11, 23],  # Sagittarius
    9: [5, 19],  # Capricorn
    10: [9, 24],  # Aquarius
    11: [11, 25],  # Pisces
}


def _pushkar_navamsha(bodies: list[dict]) -> dict:
    """Flag planets occupying Pushkar degrees within their rashi sign."""
    result = {}
    for b in bodies:
        planet = b["planet"]
        sign = b["signIndex"]
        deg = b.get("degInSign", 0)
        pushkar_range = _PUSHKAR_DEGREES.get(sign, [])
        is_pushkar = any(abs(deg - pd) < 1.0 for pd in pushkar_range)
        result[planet] = {
            "isPushkar": is_pushkar,
            "degree": round(deg, 2),
            "pushkarRange": pushkar_range if is_pushkar else [],
        }
    return result
