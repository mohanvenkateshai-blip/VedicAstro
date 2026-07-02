"""Kalachakra leap-detection + Deha/Jeeva unit tests.

Ground truth is the empirical scan documented in the Kalachakra rebuild plan
(Decision 3/4), itself validated against BPHS Vol.2 Ch.46 v.60-100's worked
examples (knowledge-graph/raw/Brihat_Parasara_Hora_Sastra_Vol_2.md).
"""

from app.kalachakra import kalachakra_cycle

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
