"""
Ashtakavarga Prediction Module — BAV + SAV transit predictions

Sources:
  - BPHS Ch.67-72 (Ashtakavarga)
  - Gochar Phaladeepika Ch.27
  - Phaladeepika Ch.19
  - Sarvartha Chintamani Ch.17

Ashtakavarga (literally "eight-fold") is the most refined transit prediction
system in Vedic astrology. Each planet contributes bindus (benefic dots) to
12 signs, creating the Bhinnashtakavarga (BAV). The sum of all 7 planets'
bindus always totals 337 (the raw/unreduced invariant) — this is the board
compute_ashtakavarga() below returns, matching every other Ashtakavarga
display in this app and this module's own SAV_BANDS thresholds (30+/28+/25+).

Transit results are predicted by the number of bindus in the sign a planet
is transiting through (from SAV) or the specific planet's BAV.
"""

from dataclasses import dataclass, field

from ..core.panchanga import PLANETS, RASHIS, rashi_index
from knowledge_engine.integration import get_structured_book, get_hierarchy_for_node, get_nodes_for_chapter, get_safe_structured_book, get_safe_nodes_for_chapter

_ashtakavarga_rules_version: str | None = None
_ashtakavarga_registered = False

# Chapter-aware caches
_akv_structured_books: dict[str, dict] = {}
_akv_book_index: dict[str, str] = {
    "BPHS": "Brihat_Parasara_Hora_Sastra_Vol_1",
    "BPHS2": "Brihat_Parasara_Hora_Sastra_Vol_2",
    "GocharPhala": "Gochar_Phaladeepika_Pulippani",
    "AshtakavargaHandbook": "Ashtakavarga_System_Comprehensive_Handbook",
}

# NOTE: this module used to hand-transcribe BAV_TABLE (per-contributor bindu
# distances) here. It's gone — compute_ashtakavarga() below delegates raw BAV
# construction to jhora.horoscope.chart.ashtakavarga.get_ashtaka_varga after a
# transcription bug was found in this table's Moon row (see compute_ashtakavarga's
# docstring). Interpretation tables (bindu bands, verdicts) remain below.

# Bindu interpretation (Gochar Phaladeepika Ch.27)
BINDU_RESULTS = {
    0: (
        "Extremely inauspicious",
        "ashubh",
        "Danger, severe loss, major health issues, avoid all important work",
    ),
    1: (
        "Highly inauspicious",
        "ashubh",
        "Significant obstacles, financial drain, conflicts, stress",
    ),
    2: ("Inauspicious", "ashubh", "Delays, minor losses, reduced success, tension"),
    3: ("Below average", "ashubh", "Struggles, some obstacles, mixed results with effort"),
    4: ("Average", "neutral", "Moderate results, normal progress, steady but unremarkable"),
    5: ("Above average", "shubh", "Good progress, some gains, supportive environment"),
    6: ("Favourable", "shubh", "Clear progress, gains, success in ventures, good health"),
    7: ("Highly favourable", "shubh", "Strong gains, happiness, success, prosperity"),
    8: (
        "Exceptionally auspicious",
        "shubh",
        "Maximum support, great success, wealth, honour, all-round prosperity",
    ),
}

# SAV band interpretation (GPD Ch.27)
SAV_BANDS = {
    "excellent": (30, 999, "shubh", "Excellent — robust support for all activities"),
    "good": (28, 29, "shubh", "Good — strong support, proceed confidently"),
    "standard": (25, 27, "neutral", "Standard — moderate support, normal progress"),
    "depleted": (0, 24, "ashubh", "Depleted — thin support, avoid major initiatives"),
}


@dataclass
class AshtakavargaResult:
    """Complete Ashtakavarga computation."""

    bav: dict  # {planet: [12 bindus per sign]}, post Trikona+Ekadhipatya Shodhana
    sav: list  # [12 total bindus], post Shodhana ("Sodhita Ashtakavarga")
    planet_totals: dict  # {planet: total bindus}
    total_sav: int  # < 337 after correct Shodhana (337 is only the raw/unreduced invariant)
    lagna_sign_idx: int = 0

    # Transit bindus
    transit_sav: dict = field(default_factory=dict)  # {planet: bindus in current transit sign}
    moon_transit_bindus: int = 0
    moon_transit_verdict: str = "neutral"
    moon_transit_band: str = ""

    # Synthesis
    summary: str = ""

    # Chapter-aware provenance from KE
    chapter_citation: str | None = None
    hierarchy_path: str | None = None


_PLANET_NAME_TO_ID = {"Sun": 0, "Moon": 1, "Mars": 2, "Mercury": 3, "Jupiter": 4, "Venus": 5, "Saturn": 6}
_PLANET_ID_TO_NAME = {v: k for k, v in _PLANET_NAME_TO_ID.items()}


def _build_chart_1d(natal_sign: dict, lagna_sign_idx: int) -> list:
    """Build PyJHora's house_to_planet_list format (12 strings, '/'-joined
    planet ids, 'L' for Lagna) from the {planet_name: sign_idx} + lagna_idx
    shape this module's callers already have.

    Rahu/Ketu (ids 7/8) are placed at a fixed nominal position (sign 0) if
    absent from natal_sign — PyJHora's get_ashtaka_varga/_ekadhipatya_sodhana
    require *some* house entry for every id in const.SUN_TO_KETU to avoid a
    KeyError, but classical Ashtakavarga's BAV/SAV math (7 planets + Lagna
    as contributors) never actually reads their positions, so this has zero
    effect on the returned bindus.
    """
    chart = ["" for _ in range(12)]
    seen_ids = set()
    for name, sign in natal_sign.items():
        pid = _PLANET_NAME_TO_ID.get(name)
        if pid is None:
            continue
        chart[sign] += f"{pid}/"
        seen_ids.add(pid)
    for placeholder_id in (7, 8):  # Rahu, Ketu — unused by BAV/SAV math
        if placeholder_id not in seen_ids:
            chart[0] += f"{placeholder_id}/"
    chart[lagna_sign_idx] += "L/"
    return [c[:-1] if c.endswith("/") else c for c in chart]


def compute_ashtakavarga(natal_sign: dict, lagna_sign_idx: int) -> AshtakavargaResult:
    """Compute Bhinnashtakavarga (BAV) and Sarvashtakavarga (SAV).

    Delegates BAV/SAV construction to jhora.horoscope.chart.ashtakavarga —
    the same validated engine app/chart.py uses for the /chart endpoint's
    Ashtakavarga block — rather than this module's own hand-transcribed
    BAV_TABLE, which had a transcription error in Moon's contribution
    distances (misplaced, though didn't lose, bindus across signs).

    Returns the RAW (pre-Shodhana) board, matching every other Ashtakavarga
    display in this app (the /chart endpoint, the portal's Ashtakavarga tab,
    Kalachakra leap-strength scoring) and this module's own SAV_BANDS
    thresholds (30+/28+/25+/depleted), which are calibrated for the raw
    0-337 scale. An earlier version applied Trikona + Ekadhipatya Shodhana
    here — correctly, once its own bugs were fixed — but that "Sodhita"
    board runs on a much smaller scale (totals ~80-90 on a real chart, not
    337), which silently broke every threshold check downstream (SAV_BANDS
    here and fructification.py's separate exceptional/strong/moderate scale)
    since nothing exceeds "30+" anymore. Shodhana's classical purpose (BPHS
    Ch.68's Sodhya Pinda technique) is a distinct, deliberate calculation —
    not something to fold into general-purpose bindu-strength lookups.

    Args:
        natal_sign: dict of planet → rashi_idx (0=Aries) for 7 planets
        lagna_sign_idx: Lagna rashi index

    Returns:
        AshtakavargaResult with raw BAV, SAV, and totals (SAV sums to 337).
    """
    from jhora.horoscope.chart import ashtakavarga as jh_ashtakavarga

    chart_1d = _build_chart_1d(natal_sign, lagna_sign_idx)
    binna, sav, _prastara = jh_ashtakavarga.get_ashtaka_varga(chart_1d)

    bav = {_PLANET_ID_TO_NAME[p]: list(binna[p]) for p in range(7)}
    planet_totals = {p: sum(bav[p]) for p in bav}
    total_sav = sum(sav)

    return AshtakavargaResult(
        bav=bav,
        sav=sav,
        planet_totals=planet_totals,
        total_sav=total_sav,
        lagna_sign_idx=lagna_sign_idx,
    )


def compute_transit_ashtakavarga(
    akv: AshtakavargaResult,
    date_str: str = None,
    time_str: str = "12:00",
    lat: float = 12.30,
    lon: float = 76.65,
    tz: float = 5.5,
) -> AshtakavargaResult:
    """Compute transit bindus for the current date using existing Ashtakavarga.

    For each transiting planet, look up how many SAV bindus are in the sign
    it's currently transiting. This is the classical transit prediction method.
    """
    # Get current planet positions
    from ..core.panchanga import compute_panchanga

    panch = compute_panchanga(date_str, time_str, lat, lon, tz)

    transit_sav = {}
    for planet in PLANETS[:7]:  # Sun through Saturn (Rahu/Ketu excluded)
        row = next((t for t in panch.transit if t["planet"] == planet), None)
        if row:
            sign_idx = rashi_index(row["lon"])
            transit_sav[planet] = {
                "sign": RASHIS[sign_idx],
                "bindus": akv.sav[sign_idx],
                "band": _get_band(akv.sav[sign_idx]),
                "verdict": _get_band(akv.sav[sign_idx])[2],
            }

    # Moon transit bindus (most important — used for Muhurta)
    moon_sign_idx = rashi_index(next((t["lon"] for t in panch.transit if t["planet"] == "Moon"), 0))
    moon_bindus = akv.sav[moon_sign_idx]
    akv.moon_transit_bindus = moon_bindus
    akv.moon_transit_band = _get_band(moon_bindus)[0]
    akv.moon_transit_verdict = _get_band(moon_bindus)[2]

    akv.transit_sav = transit_sav

    # Build summary. Note: 337 is the raw/unreduced SAV invariant — this board
    # is post Trikona+Ekadhipatya Shodhana ("Sodhita Ashtakavarga"), which
    # legitimately totals less than 337.
    lines = [f"Sodhita Ashtakavarga SAV total: {akv.total_sav} (raw invariant: 337)"]
    lines.append(
        f"Moon transiting {RASHIS[moon_sign_idx]} with {moon_bindus} bindus — {_get_band(moon_bindus)[3]}"
    )
    lines.append("")

    for sign_idx in range(12):
        line = f"  {RASHIS[sign_idx]:12s} "
        bar = "█" * (akv.sav[sign_idx] // 2) + "░" * (16 - akv.sav[sign_idx] // 2)
        line += f"{bar} {akv.sav[sign_idx]:2d}"
        lines.append(line)

    akv.summary = "\n".join(lines)

    # Chapter-aware provenance (structured chapters + patch)
    try:
        prov = _resolve_akv_citation()
        if prov:
            akv.chapter_citation = prov.get("citation")
            akv.hierarchy_path = prov.get("hierarchy_path")
    except Exception:
        pass

    return akv


def _get_band(bindus: int) -> tuple:
    """Get the SAV band for a given number of bindus."""
    if bindus >= 30:
        return SAV_BANDS["excellent"]
    if bindus >= 28:
        return SAV_BANDS["good"]
    if bindus >= 25:
        return SAV_BANDS["standard"]
    return SAV_BANDS["depleted"]


def bindu_prediction(bindus: int) -> dict:
    """Get prediction for a specific bindu count (0-8)."""
    return {
        "count": bindus,
        "label": BINDU_RESULTS.get(bindus, ("Unknown", "neutral", ""))[0],
        "verdict": BINDU_RESULTS.get(bindus, ("", "neutral", ""))[1],
        "effect": BINDU_RESULTS.get(bindus, ("", "", ""))[2],
    }


def _clear_ashtakavarga_knowledge_caches() -> None:
    """Drop graph caches on refresh for ashtakavarga."""
    try:
        from knowledge_engine.integration import clear_knowledge_engine_cache

        clear_knowledge_engine_cache()
    except Exception:
        pass


def _on_ashtakavarga_refresh(new_version: str) -> None:
    global _ashtakavarga_rules_version, _akv_structured_books
    _ashtakavarga_rules_version = new_version
    _clear_ashtakavarga_knowledge_caches()
    _akv_structured_books = {}
    # Real consumption: load structured chapters for ashtakavarga (BPHS Ch.67-72, handbook)
    for key, book_id in _akv_book_index.items():
        try:
            data = get_safe_structured_book(book_id) or get_structured_book(book_id)
            if data:
                _akv_structured_books[book_id] = data
                if "BPHS" in key:
                    get_safe_nodes_for_chapter(book_id, "ch-67")
        except Exception:
            pass


def _register_ashtakavarga_engine() -> None:
    global _ashtakavarga_registered
    if _ashtakavarga_registered:
        return
    try:
        from knowledge_engine.integration import get_knowledge_engine

        get_knowledge_engine().register_engine("ashtakavarga", on_refresh=_on_ashtakavarga_refresh)
        _ashtakavarga_registered = True
    except Exception:
        pass


_register_ashtakavarga_engine()


def _ensure_ashtakavarga_registered() -> None:
    if not _ashtakavarga_registered:
        _register_ashtakavarga_engine()


def _resolve_akv_citation() -> dict | None:
    """Resolve ashtakavarga to chapter citation using structured book + patch provenance."""
    book_id = _akv_book_index.get("BPHS") or _akv_book_index.get("AshtakavargaHandbook")
    data = _akv_structured_books.get(book_id) or get_structured_book(book_id)
    if not data:
        return None
    chapters = data.get("chapters") or []
    chosen = None
    for ch in chapters:
        t = ((ch.get("title") or "") + " " + (ch.get("id") or "")).lower()
        if any(k in t for k in ["ashtakavarga", "67", "68", "69", "70", "71", "72", "bindu", "bav", "sav"]):
            chosen = ch
            break
    if not chosen and chapters:
        chosen = chapters[0]
    if not chosen:
        return None
    hier = None
    conf = None
    ch_nodes = (data.get("chapter_node_ids") or {}).get(chosen.get("id")) or []
    if ch_nodes:
        h = get_hierarchy_for_node(ch_nodes[0])
        if h:
            hier = h.get("hierarchy_path")
            conf = h.get("confidence")
    citation = f"{data.get('canonical_name') or book_id} — {chosen.get('title') or chosen.get('id')}"
    if hier:
        citation = f"{citation} (per {hier})"
    return {"citation": citation, "hierarchy_path": hier or chosen.get("id"), "chapter_id": chosen.get("id"), "confidence": conf}
