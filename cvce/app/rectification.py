"""Birth-time rectification via multi-dasha confluence scoring.

Given an approximate birth time and a set of real, precisely-dated life
events, sweeps candidate birth times (minute-by-minute across a window) and
scores each candidate by how well multiple *independent* dasha systems'
running lords match that chart's own house-lordship-specific significators
for each event's life domain.

Two things this deliberately does NOT do, both by design:
1. Match on generic textbook karakas alone (e.g. "Jupiter = children,
   always"). Each candidate time gets its own Ascendant, so house
   lordships (which planet actually rules the 5th/7th/10th/etc. from THIS
   lagna) are recomputed per candidate — a hit only counts if it's specific
   to that chart, not a one-size-fits-all guess.
2. Score any single dasha system in isolation. Per explicit guidance from
   the user's own Jyotish guru — real event timing requires cross-
   referencing multiple systems together (their example: Vimshottari +
   Yogini for one event) — agreement across systems is scored as a
   confluence bonus, not just summed hit counts from one system.

Deeper dasha levels (Pratyantardasha/Sookshma/Prana) score higher than
shallow ones (Mahadasha/Antardasha) since they're a more specific signal —
a Prana-level hit lands on a period of days, a Mahadasha-level hit on a
period of years.
"""

from __future__ import annotations

from datetime import date as _date
from datetime import datetime, timedelta

from app.dasha_vimshottari import running_ladder
from app.ephem import ascendant, jd_place, parse_dt, set_ayanamsa

RASHIS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

# House(s) + universal karaka(s) relevant to each life-event domain. House
# lordship is resolved per-candidate-lagna at scoring time — this table is
# just "which houses/karakas matter for this kind of event," not an answer.
DOMAIN_HOUSES: dict[str, dict] = {
    "marriage": {"houses": [7], "karakas": ["Venus"]},
    "children": {"houses": [5], "karakas": ["Jupiter"]},
    "career_status": {"houses": [10], "karakas": ["Sun", "Saturn"]},
    "career_obstacle": {"houses": [6], "karakas": []},
    "mother": {"houses": [4], "karakas": ["Moon"]},
    "father": {"houses": [9], "karakas": ["Sun"]},
    "death_loss": {"houses": [8, 12], "karakas": ["Saturn"]},
}

# Deeper dasha levels are a more specific signal (a Prana-level hit lands on
# a window of days; a Mahadasha-level hit on a window of years).
_LEVEL_WEIGHT = {1: 1.0, 2: 1.6, 3: 2.4, 4: 3.4, 5: 4.6}
_CONFLUENCE_BONUS = 3.0


def _house_lord(lagna_idx: int, house: int) -> str:
    sign = RASHIS[(lagna_idx + house - 1) % 12]
    return SIGN_LORDS[sign]


def _domain_significators(domain: str, lagna_idx: int) -> set[str]:
    spec = DOMAIN_HOUSES[domain]
    sig = set(spec.get("karakas") or [])
    for h in spec["houses"]:
        sig.add(_house_lord(lagna_idx, h))
    return sig


def _yogini_blocks(jd: float, place, dt: datetime) -> list[dict]:
    """Full-life Yogini Mahadasha blocks (each with its Antardashas), as
    real `date` objects so an arbitrary query date can be looked up.

    A lighter, date-parameterizable sibling of the block-building half of
    app.dasha_other.yogini_deep_payload (that function hardcodes "today"
    for its running ladder — not reusable here where we need to query many
    different historical event dates against many different candidate
    birth times).
    """
    from jhora import const
    from jhora.horoscope.dhasa.graha import yogini
    from jhora.panchanga.drik import Date as DrikDate
    from jhora.panchanga.drik import dhasa_year_duration

    from app.dasha_other import YOGINI_TOTAL_YEARS, YOGINI_YEARS, _lord_name

    year_dur = dhasa_year_duration(jd=jd, place=place)
    flat_maha = yogini.get_dhasa_bhukthi(
        DrikDate(dt.year, dt.month, dt.day),
        (dt.hour, dt.minute, dt.second),
        place,
        dhasa_level_index=const.MAHA_DHASA_DEPTH.MAHA_DHASA_ONLY,
        round_duration=False,
    )
    blocks = []
    for row in flat_maha:
        lords, st, dur = row[0], row[1], float(row[2])
        maha_pid = lords[0] if isinstance(lords, (list, tuple)) else lords
        maha_years = YOGINI_YEARS.get(maha_pid, 1)
        maha_start = _date(int(st[0]), int(st[1]), int(st[2]))
        maha_end = maha_start + timedelta(days=int(round(dur * year_dur)))

        antar_pids = yogini._antardhasa(maha_pid, antardhasa_option=1)
        antars = []
        cursor = maha_start
        for antar_pid in antar_pids:
            antar_years = YOGINI_YEARS.get(antar_pid, 1)
            antar_days = int(round(maha_years * antar_years * year_dur / YOGINI_TOTAL_YEARS))
            antar_end = cursor + timedelta(days=antar_days)
            antars.append({"lord": _lord_name(antar_pid), "start": cursor, "end": antar_end})
            cursor = antar_end

        blocks.append({"lord": _lord_name(maha_pid), "start": maha_start, "end": maha_end, "antars": antars})
    return blocks


def _vimshottari_hits(jd: float, place, event_jd: float, domain_sigs: set[str]) -> list[dict]:
    ladder = running_ladder(jd, place, query_jd=event_jd, depth=5)
    return [
        {"system": "Vimshottari", "level": row["level"], "levelLabel": row["levelLabel"], "planet": row["lord"]}
        for row in ladder
        if row["lord"] in domain_sigs
    ]


def _yogini_hits(blocks: list[dict], event_date: _date, domain_sigs: set[str]) -> list[dict]:
    hits = []
    for b in blocks:
        if not (b["start"] <= event_date <= b["end"]):
            continue
        if b["lord"] in domain_sigs:
            hits.append({"system": "Yogini", "level": 1, "levelLabel": "Mahadasha", "planet": b["lord"]})
        for a in b["antars"]:
            if a["start"] <= event_date <= a["end"]:
                if a["lord"] in domain_sigs:
                    hits.append({"system": "Yogini", "level": 2, "levelLabel": "Antardasha", "planet": a["lord"]})
                break
        break
    return hits


def _score_hits(hits: list[dict]) -> float:
    if not hits:
        return 0.0
    base = sum(_LEVEL_WEIGHT.get(h["level"], 1.0) for h in hits)
    systems_hit = {h["system"] for h in hits}
    return base + (_CONFLUENCE_BONUS if len(systems_hit) > 1 else 0.0)


def rectify_birth_time(
    approx_datetime: str,
    lat: float,
    lon: float,
    tz: float,
    events: list[dict],
    window_minutes: int = 30,
    ayanamsa: str = "LAHIRI",
) -> dict:
    """events: [{"date": "YYYY-MM-DD", "time": "HH:MM" | None, "domain": str, "label": str}]

    Returns candidates sorted by total_score descending, each with a full
    per-event hit breakdown (which system, which level, which planet, why
    it counts) — explainable, not a black-box ranking.
    """
    set_ayanamsa(ayanamsa)
    base_dt = parse_dt(approx_datetime)

    candidates = []
    for offset in range(-window_minutes, window_minutes + 1):
        cand_dt = base_dt + timedelta(minutes=offset)
        jd, place = jd_place(cand_dt, lat, lon, tz)
        lagna_idx = ascendant(jd, place)["signIndex"]
        yogini_blocks = _yogini_blocks(jd, place, cand_dt)

        total = 0.0
        breakdown = []
        for ev in events:
            domain = ev["domain"]
            sigs = _domain_significators(domain, lagna_idx)
            ev_dt_str = f"{ev['date']}T{ev.get('time') or '12:00'}:00"
            ev_jd, _ = jd_place(parse_dt(ev_dt_str), lat, lon, tz)
            ev_date = _date.fromisoformat(ev["date"])

            hits = _vimshottari_hits(jd, place, ev_jd, sigs) + _yogini_hits(yogini_blocks, ev_date, sigs)
            score = _score_hits(hits)
            total += score
            breakdown.append(
                {
                    "label": ev.get("label", ev["date"]),
                    "domain": domain,
                    "significators": sorted(sigs),
                    "hits": hits,
                    "score": round(score, 2),
                }
            )

        candidates.append(
            {
                "offset_minutes": offset,
                "datetime": cand_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                "lagna": RASHIS[lagna_idx],
                "total_score": round(total, 2),
                "breakdown": breakdown,
            }
        )

    candidates.sort(key=lambda c: c["total_score"], reverse=True)
    return {"approx_datetime": approx_datetime, "window_minutes": window_minutes, "candidates": candidates}
