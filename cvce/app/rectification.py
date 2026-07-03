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


def _proximity(event_date: _date, start: str, end: str) -> float:
    """How centered `event_date` is within a [start,end] period: 1.0 dead
    center, tapering toward the edges but floored at 0.35 (a real hit near a
    boundary still counts, just discounted). This is the key v2 noise-damper:
    a 1-minute birth shift that nudges an event just across a deep-level
    period boundary now degrades the score smoothly instead of binary-
    flipping it full→zero, which was the dominant source of the jagged v1
    landscape.
    """
    s = _date.fromisoformat(start)
    e = _date.fromisoformat(end)
    span = (e - s).days
    if span <= 0:
        return 1.0
    center = s + timedelta(days=span / 2)
    dist = abs((event_date - center).days)
    frac = 1.0 - (dist / (span / 2))  # 1 at center → 0 at edge
    return max(0.35, frac)


def _vimshottari_hits(jd: float, place, event_jd: float, event_date: _date, domain_sigs: set[str]) -> list[dict]:
    ladder = running_ladder(jd, place, query_jd=event_jd, depth=5)
    hits = []
    for row in ladder:
        if row["lord"] in domain_sigs:
            hits.append({
                "system": "Vimshottari", "level": row["level"], "levelLabel": row["levelLabel"],
                "planet": row["lord"], "proximity": round(_proximity(event_date, row["start"], row["end"]), 3),
            })
    return hits


def _yogini_hits(blocks: list[dict], event_date: _date, domain_sigs: set[str]) -> list[dict]:
    hits = []
    for b in blocks:
        if not (b["start"] <= event_date <= b["end"]):
            continue
        if b["lord"] in domain_sigs:
            hits.append({"system": "Yogini", "level": 1, "levelLabel": "Mahadasha", "planet": b["lord"],
                         "proximity": round(_proximity(event_date, b["start"].isoformat(), b["end"].isoformat()), 3)})
        for a in b["antars"]:
            if a["start"] <= event_date <= a["end"]:
                if a["lord"] in domain_sigs:
                    hits.append({"system": "Yogini", "level": 2, "levelLabel": "Antardasha", "planet": a["lord"],
                                 "proximity": round(_proximity(event_date, a["start"].isoformat(), a["end"].isoformat()), 3)})
                break
        break
    return hits


def _score_hits(hits: list[dict]) -> float:
    """Proximity-weighted, confluence-rewarded. Each hit contributes its
    level weight × how centered the event is in that period. Cross-system
    agreement (Vimshottari + Yogini both flagging a significator) adds a
    bonus, per the classical multi-system principle — a lone deep-level
    coincidence stays cheap; genuine confluence is what scores."""
    if not hits:
        return 0.0
    base = sum(_LEVEL_WEIGHT.get(h["level"], 1.0) * h.get("proximity", 1.0) for h in hits)
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

            hits = _vimshottari_hits(jd, place, ev_jd, ev_date, sigs) + _yogini_hits(yogini_blocks, ev_date, sigs)
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

    # Stable-cluster analysis: a trustworthy rectified time is a *plateau*
    # of consistently high scores, not a lone spike (which is noise). Slide a
    # window over the by-clock-time ordering and find the highest-mean run;
    # its center is a far more defensible recommendation than argmax.
    by_time = sorted(candidates, key=lambda c: c["offset_minutes"])
    cluster = _best_cluster(by_time, width=5)

    candidates_by_score = sorted(candidates, key=lambda c: c["total_score"], reverse=True)
    peak = candidates_by_score[0]
    recommendation = _recommendation(peak, cluster, by_time)

    return {
        "approx_datetime": approx_datetime,
        "window_minutes": window_minutes,
        "recommendation": recommendation,
        "stable_cluster": cluster,
        "peak_candidate": {"datetime": peak["datetime"], "total_score": peak["total_score"], "offset_minutes": peak["offset_minutes"]},
        "candidates": candidates_by_score,
    }


def _best_cluster(by_time: list[dict], width: int = 5) -> dict:
    """Highest-mean contiguous run of `width` candidates (a score plateau)."""
    best = None
    half = width // 2
    for i in range(half, len(by_time) - half):
        window = by_time[i - half : i + half + 1]
        mean = sum(c["total_score"] for c in window) / len(window)
        if best is None or mean > best["mean_score"]:
            center = by_time[i]
            best = {
                "center_datetime": center["datetime"],
                "center_offset_minutes": center["offset_minutes"],
                "mean_score": round(mean, 2),
                "width_minutes": width,
                "member_offsets": [c["offset_minutes"] for c in window],
            }
    return best or {}


def _recommendation(peak: dict, cluster: dict, by_time: list[dict]) -> dict:
    """Honest verdict: only endorse a rectified time when the peak sits inside
    a genuine plateau AND stands clearly above the field. Otherwise say so —
    a noisy landscape means the recorded time should stand, not that we should
    hand back a spurious minute.
    """
    scores = [c["total_score"] for c in by_time]
    mean_all = sum(scores) / len(scores) if scores else 0.0
    peak_in_cluster = cluster and peak["offset_minutes"] in (cluster.get("member_offsets") or [])
    # signal-to-noise: how far the best plateau rises above the overall mean
    lift = (cluster.get("mean_score", 0.0) - mean_all) if cluster else 0.0
    strong = bool(peak_in_cluster and lift >= 0.25 * mean_all and mean_all > 0)
    return {
        "confident": strong,
        "suggested_datetime": cluster.get("center_datetime") if strong else None,
        "note": (
            f"Plateau near {cluster.get('center_datetime','?')[11:16]} rises "
            f"clearly above the field (cluster mean {cluster.get('mean_score')} vs overall {round(mean_all,2)}) — a defensible rectified time."
            if strong else
            "No stable plateau clearly beats the field — landscape is noise-dominated. "
            "Recorded time should stand; minute-level dasha rectification is at its limit for this data."
        ),
    }
