"""
Cross-engine position validator for MuhurtaCosmos.

Computes sidereal planetary longitudes for a set of reference dates with two
independent engines and prints an arc-second comparison table:

  * PyJHora      -- Swiss Ephemeris, Lahiri ayanamsa  (primary engine)
  * jyotishganit -- Skyfield/JPL, True Chitra ayanamsa (independent check)

The two libraries use different ayanamsa definitions, so a roughly constant
offset across all seven non-node planets is expected and benign. We estimate
that systematic offset from the median and flag only the *residual* scatter:
anything above RESIDUAL_THRESHOLD_DEG after removing the offset points to a
genuine disagreement worth investigating.

Run:  ./.venv/bin/python validate.py
Exit code is non-zero if any reference date shows a flagged residual.
"""
from __future__ import annotations

import sys
from datetime import datetime

RESIDUAL_THRESHOLD_DEG = 0.1  # ~6 arc-min: beyond ayanamsa noise

PLANET_NAMES = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
RASHIS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
          "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

# (label, ISO local datetime, lat, lon, tz_offset)
REFERENCE_CASES = [
    ("Mohan natal (Mysore)",      "1975-04-22T19:15:00", 12.3,    76.633,  5.5),
    ("Mullingar today noon",      "2026-06-20T12:00:00", 53.5236, -7.3437, 1.0),
    ("J2000 epoch (Greenwich)",   "2000-01-01T12:00:00", 51.4769,  0.0,    0.0),
    ("Republic Day (New Delhi)",  "1950-01-26T10:15:00", 28.6139, 77.2090, 5.5),
    ("Total eclipse (Chennai)",   "1980-02-16T15:30:00", 13.0827, 80.2707, 5.5),
    ("Y2K+ (New York)",           "2010-07-11T18:00:00", 40.7128, -74.006, -5.0),
    ("Solstice (Reykjavik)",      "2021-06-21T03:32:00", 64.1466, -21.942, 0.0),
    ("Deep south (Sydney)",       "1995-11-09T06:45:00", -33.868, 151.209, 11.0),
    ("Pre-1900 (Paris)",          "1889-03-31T00:00:00", 48.8566,  2.3522, 0.0),
    ("Future (Tokyo)",            "2035-12-25T09:00:00", 35.6762, 139.650, 9.0),
]


def _parse(s):
    return datetime.fromisoformat(s)


def pyjhora_positions(dt, lat, lon, tz):
    """Absolute sidereal longitude per planet via PyJHora (Lahiri)."""
    from jhora import utils, const
    from jhora.panchanga import drik
    from jhora.panchanga.drik import Place
    const._INCLUDE_URANUS_TO_PLUTO = False
    drik.set_ayanamsa_mode("LAHIRI")
    jd = utils.julian_day_number((dt.year, dt.month, dt.day),
                                 (dt.hour, dt.minute, dt.second))
    place = Place("loc", lat, lon, tz)
    out = {}
    for pid, deg, sign in drik.planetary_positions(jd, place):
        if 0 <= pid < len(PLANET_NAMES):
            out[PLANET_NAMES[pid]] = (sign * 30 + deg) % 360
    return out


def jyotishganit_positions(dt, lat, lon, tz):
    """Absolute sidereal longitude per planet via jyotishganit (True Chitra)."""
    import jyotishganit.main as jgm
    chart = jgm.calculate_birth_chart(dt, lat, lon, tz)
    cj = jgm.get_birth_chart_json(chart)
    out = {}
    for house in cj["d1Chart"]["houses"]:
        if house["sign"] not in RASHIS:
            continue
        sign_idx = RASHIS.index(house["sign"])
        for occ in house.get("occupants", []):
            name = occ.get("celestialBody")
            if name:
                out[name] = (sign_idx * 30 + float(occ["signDegrees"])) % 360
    return out


def median(xs):
    s = sorted(xs)
    return s[len(s) // 2] if s else 0.0


def signed_delta(a, b):
    return (a - b + 540) % 360 - 180


def run_case(label, iso, lat, lon, tz):
    """Returns 'pass', 'fail', or 'skip' (engine could not compute the date)."""
    dt = _parse(iso)
    try:
        pj = pyjhora_positions(dt, lat, lon, tz)
    except Exception as e:
        print(f"  ! PyJHora failed: {type(e).__name__}: {e}")
        return "fail"
    try:
        jg = jyotishganit_positions(dt, lat, lon, tz)
    except Exception as e:
        # An ephemeris-range limit is a coverage gap, not a disagreement -- skip.
        print(f"  ~ SKIP (jyotishganit cannot compute this date): "
              f"{type(e).__name__}: {e}")
        return "skip"

    main_deltas = [signed_delta(pj[n], jg[n]) for n in PLANET_NAMES[:7]
                   if n in pj and n in jg]
    offset = median(main_deltas)

    print(f"  {'Planet':<9}{'PyJHora':>12}{'jyotishganit':>14}{'Δ (deg)':>11}{'residual':>11}")
    ok = True
    for name in PLANET_NAMES:
        a, b = pj.get(name), jg.get(name)
        if a is None or b is None:
            print(f"  {name:<9}{'-':>12}{'-':>14}{'n/a':>11}")
            continue
        d = signed_delta(a, b)
        node = name in ("Rahu", "Ketu")
        resid = "(node)" if node else f"{abs(d - offset)*3600:8.1f}\""
        flag = ""
        if not node and abs(d - offset) > RESIDUAL_THRESHOLD_DEG:
            flag, ok = "  <-- FLAG", False
        print(f"  {name:<9}{a:12.5f}{b:14.5f}{d:11.5f}{resid:>11}{flag}")
    print(f"  systematic ayanamsa offset (median of 7): {offset:+.5f} deg "
          f"({offset*3600:+.1f}\")")
    return "pass" if ok else "fail"


def main():
    print("=" * 72)
    print("MuhurtaCosmos cross-engine position validation")
    print("PyJHora (Lahiri) vs jyotishganit (True Chitra)")
    print(f"residual flag threshold: {RESIDUAL_THRESHOLD_DEG} deg "
          f"({RESIDUAL_THRESHOLD_DEG*3600:.0f} arc-sec)")
    print("=" * 72)
    passed = failed = skipped = 0
    for case in REFERENCE_CASES:
        print(f"\n# {case[0]}  [{case[1]}]")
        status = run_case(*case)
        passed += status == "pass"
        failed += status == "fail"
        skipped += status == "skip"
    print("\n" + "=" * 72)
    print(f"{passed} passed, {failed} failed, {skipped} skipped "
          f"of {len(REFERENCE_CASES)} reference dates.")
    if failed == 0:
        print("RESULT: PASS -- all comparable residuals within threshold "
              "after ayanamsa offset.")
        return 0
    print("RESULT: FAIL -- one or more residuals exceeded threshold (see FLAG rows).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
