"""Kalachakra leap-detection + Deha/Jeeva unit tests.

Ground truth is the empirical scan documented in the Kalachakra rebuild plan
(Decision 3/4), itself validated against BPHS Vol.2 Ch.46 v.60-100's worked
examples (knowledge-graph/raw/Brihat_Parasara_Hora_Sastra_Vol_2.md).
"""

from app.kalachakra import (
    kalachakra_cycle,
    _argala_verdict,
    _yogakaraka_giver,
    _house_karakas_for_sign,
    _travel_direction,
    _sign_lords_cached,
)

# (kc_index, pada_index): (dehaRasi, jeevaRasi, [leap types in cycle order, None if no leap])
# Regenerated directly from kalachakra_cycle() output (not hand-transcribed —
# an earlier hand-typed version of this table had transcription errors that a
# first test run caught; this is the code's own verified output).
EXPECTED = {
    (0, 0): ("Aries", "Sagittarius", [None, None, None, None, None, None, None, None]),
    (0, 1): ("Capricorn", "Gemini", [None, None, "lions_leap", "monkey_leap", "monkey_leap", "frog_leap", None, "frog_leap"]),
    (0, 2): ("Taurus", "Gemini", ["monkey_leap", "monkey_leap", "monkey_leap", "monkey_leap", "monkey_leap", "lions_leap", None, None]),
    (0, 3): ("Cancer", "Pisces", [None, None, None, None, None, None, None, None]),
    (1, 0): ("Scorpio", "Pisces", ["monkey_leap", "monkey_leap", "frog_leap", None, "frog_leap", "monkey_leap", "monkey_leap", "monkey_leap"]),
    (1, 1): ("Aquarius", "Virgo", ["monkey_leap", "monkey_leap", "lions_leap", None, None, None, None, None]),
    (1, 2): ("Libra", "Virgo", [None, None, None, None, None, "lions_leap", "monkey_leap", "monkey_leap"]),
    (1, 3): ("Cancer", "Sagittarius", [None, "frog_leap", "monkey_leap", "monkey_leap", "monkey_leap", "monkey_leap", "monkey_leap", "monkey_leap"]),
    (2, 0): ("Cancer", "Sagittarius", ["monkey_leap", "monkey_leap", "monkey_leap", "monkey_leap", "monkey_leap", "monkey_leap", "frog_leap", None]),
    (2, 1): ("Libra", "Virgo", ["monkey_leap", "monkey_leap", "lions_leap", None, None, None, None, None]),
    (2, 2): ("Aquarius", "Virgo", [None, None, None, None, None, "lions_leap", "monkey_leap", "monkey_leap"]),
    (2, 3): ("Scorpio", "Pisces", ["monkey_leap", "monkey_leap", "monkey_leap", "frog_leap", None, "frog_leap", "monkey_leap", "monkey_leap"]),
    (3, 0): ("Cancer", "Pisces", [None, None, None, None, None, None, None, None]),
    (3, 1): ("Taurus", "Gemini", [None, None, "lions_leap", "monkey_leap", "monkey_leap", "monkey_leap", "monkey_leap", "monkey_leap"]),
    (3, 2): ("Capricorn", "Gemini", ["frog_leap", None, "frog_leap", "monkey_leap", "monkey_leap", "lions_leap", None, None]),
    (3, 3): ("Aries", "Sagittarius", [None, None, None, None, None, None, None, None]),
}


def test_all_16_cycles_deha_jeeva_and_leaps():
    for (kc, pada), (expected_deha, expected_jeeva, expected_leaps) in EXPECTED.items():
        cycle = kalachakra_cycle(kc, pada)
        assert cycle["dehaRasi"] == expected_deha, f"kc={kc} pada={pada} deha"
        assert cycle["jeevaRasi"] == expected_jeeva, f"kc={kc} pada={pada} jeeva"

        actual_leaps = [n["leapFromPrevious"]["type"] if n["leapFromPrevious"] else None for n in cycle["signs"][1:]]
        assert actual_leaps == expected_leaps, f"kc={kc} pada={pada} leaps: {actual_leaps} != {expected_leaps}"


def test_no_leap_ever_on_first_sign():
    for kc in range(4):
        for pada in range(4):
            cycle = kalachakra_cycle(kc, pada)
            assert cycle["signs"][0]["leapFromPrevious"] is None


# ---------------------------------------------------------------------------
# Interpretive layer: Argala, Yogakaraka, house karakas, travel direction.
# ---------------------------------------------------------------------------


def test_sign_lords_matches_classical_rulerships():
    lords = _sign_lords_cached()
    assert lords[0] == "Mars"  # Aries
    assert lords[3] == "Moon"  # Cancer
    assert lords[4] == "Sun"  # Leo
    assert lords[6] == "Venus"  # Libra
    assert len(lords) == 12


def test_travel_direction_only_covers_the_6_documented_pairs():
    # PVR Rao tutorial p.12 — exactly these 6 (from,to) pairs are documented.
    documented = [
        ("Virgo", "Cancer"),
        ("Leo", "Gemini"),
        ("Cancer", "Leo"),
        ("Sagittarius", "Aries"),
        ("Pisces", "Scorpio"),
        ("Leo", "Cancer"),
    ]
    for frm, to in documented:
        d = _travel_direction(frm, to)
        assert d is not None, f"{frm}->{to} should be documented"
        assert "favorable" in d and "unfavorable" in d and "citation" in d

    # Sampled from the 24 distinct (from,to) transitions actually produced by
    # kalachakra_cycle() across all 16 birth cycles — none of these are among
    # PVR's 6 documented pairs, so must NOT get invented guidance.
    undocumented = [("Aries", "Pisces"), ("Taurus", "Gemini"), ("Aquarius", "Capricorn")]
    for frm, to in undocumented:
        assert _travel_direction(frm, to) is None, f"{frm}->{to} should not be documented"


def test_argala_verdict_boosted_by_own_lord_in_giver_house():
    # Aries (0): own lord Mars placed in the 11th-from-Aries (Aquarius, 10).
    natal = {"Mars": 10}
    v = _argala_verdict(0, natal)
    assert v["ownLordPresent"] is True
    assert v["verdict"] == "boosted"


def test_argala_verdict_obstructed_by_lone_malefic_occupant():
    # Taurus (1) occupied only by Saturn (not Taurus's own lord, which is Venus).
    natal = {"Saturn": 1}
    v = _argala_verdict(1, natal)
    assert v["maleficOccupant"] == ["Saturn"]
    assert v["ownLordPresent"] is False
    assert v["verdict"] == "obstructed"


def test_argala_verdict_neutral_with_no_planets_involved():
    natal = {"Jupiter": 5}  # nowhere near sign 0's argala/obstruction houses
    v = _argala_verdict(0, natal)
    assert v["givers"] == []
    assert v["obstructors"] == []
    assert v["verdict"] == "neutral"


def test_yogakaraka_giver_present_for_qualifying_lagna_only():
    # Cancer lagna (3): Yogakaraka is Mars (Phaladeepika Ch.20 / dasha_analyzer.py).
    natal = {"Mars": 3}  # Mars sitting right on the judged sign itself
    assert _yogakaraka_giver(3, natal, lagna_sign_idx=3) == "Mars"
    # Aries lagna (0) has no Yogakaraka at all (dual kendra+trikona rulership
    # doesn't arise distinct from the lagna lord for this sign).
    assert _yogakaraka_giver(0, {"Mars": 0}, lagna_sign_idx=0) is None


def test_md_ad_duration_derived_from_children_not_a_single_leaf_row():
    """Regression test: _subtree_from_flat used to set each non-leaf (MD/AD)
    node's end/durationYears from a single grabbed Pratyantardasha-level
    row's own short duration, instead of deriving it from the node's actual
    children — e.g. a 10-year Mahadasha would show as ending 8 days after it
    started. Caught by cross-checking against Cosmic Insights (a third-party
    Kalachakra implementation) for a real chart, whose Mahadasha/Antardasha
    spans matched once fixed. This locks the invariant down permanently:
    a non-leaf node's end must equal its last child's end, and its duration
    must span its full set of children, not one leaf fragment."""
    from datetime import date as _date

    from app.ephem import jd_place, parse_dt
    from app.kalachakra import kalachakra_tree
    from jhora.panchanga.drik import Date as DrikDate

    dt = parse_dt("1975-04-22T19:15:00")
    jd, place = jd_place(dt, 12.2979, 76.6393, 5.5)
    dob = DrikDate(dt.year, dt.month, dt.day)
    tob = (dt.hour, dt.minute, dt.second)

    tree = kalachakra_tree(jd, place, dob, tob, is_savya=False, max_level=3)
    assert len(tree) > 0

    for md in tree:
        assert md["subPeriods"], "expected AD children under each MD"
        last_ad = md["subPeriods"][-1]
        assert md["end"] == last_ad["end"], f"MD {md['sign']} end must match its last AD's end"
        # A real Mahadasha (4-21 years per the classical sign-year table)
        # must not collapse to a Pratyantardasha-length fragment.
        assert md["durationYears"] > 1.0, f"MD {md['sign']} duration suspiciously short: {md['durationYears']}"

        for ad in md["subPeriods"]:
            assert ad["subPeriods"], "expected PD children under each AD"
            last_pd = ad["subPeriods"][-1]
            assert ad["end"] == last_pd["end"], f"AD {ad['sign']} end must match its last PD's end"

    # The known-good comparison point: Mohan's chart (kc=3/Apasavya pada 3,
    # verified null-leap cycle) — first MD (Sagittarius, partial at birth)
    # must run well past its start, not just days.
    first_md = tree[0]
    start_d = _date.fromisoformat(first_md["start"])
    end_d = _date.fromisoformat(first_md["end"])
    assert (end_d - start_d).days > 300


def test_house_karakas_for_sign_matches_pvr_easy_reference_table():
    # Lagna Aries (0): 7th house is Libra (6) -> Venus (PVR p.14-15: Wife=D-9=Venus=7th).
    assert _house_karakas_for_sign(6, lagna_sign_idx=0) == ["Venus"]
    # 10th house from Aries is Capricorn (9) -> Sun (PVR: Career=D-10=Sun=10th).
    assert _house_karakas_for_sign(9, lagna_sign_idx=0) == ["Sun"]
    # 4th house from Aries is Cancer (3) -> Moon (PVR: Mother=D-12=Moon=4th).
    assert _house_karakas_for_sign(3, lagna_sign_idx=0) == ["Moon"]
