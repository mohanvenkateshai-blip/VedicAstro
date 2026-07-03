"""Tests for the prioritized/timed/remedied yoga predictions
(report_facts.py:_priority_predictions) — the redesign replacing "40 yogas,
each labeled moderate" with a small, chart-specific, timed set.
"""

from app.ephem import jd_place, parse_dt
from app.report_facts import build_report_facts
from app.remedies import _reads_negative, remedy_for_yoga


def test_reads_negative_ignores_positive_flip_phrasing():
    # "overcomes X" / "triumph over X" / "success through X" are auspicious
    # framings that happen to contain a negative-sounding noun.
    assert _reads_negative("Happiness, good fortune, overcomes enemies") is False
    assert _reads_negative("Success through adversity, triumph over enemies") is False
    assert _reads_negative("Talkative, wise, strong, leader, eloquent") is False


def test_reads_negative_catches_genuine_affliction_text():
    assert _reads_negative("Frequently loses fortune; mental grief, insignificant") is True
    assert _reads_negative("Distress to elders, trouble from enemies or weapons") is True
    assert _reads_negative("Loss, reversal, distress to father") is True


def test_remedy_for_yoga_none_for_positive_yoga_with_no_affliction():
    dignity = {"Jupiter": "own"}
    assert remedy_for_yoga(["Jupiter"], dignity, "Happiness, good fortune, overcomes enemies") is None


def test_remedy_for_yoga_debilitated_planet_takes_priority():
    dignity = {"Saturn": "debilitated"}
    r = remedy_for_yoga(["Saturn"], dignity, "Happiness, good fortune")
    assert r is not None
    assert r["theme"] == "debilitated_planet"


def test_remedy_for_yoga_negative_text_with_natural_malefic():
    dignity = {"Saturn": "neutral"}
    r = remedy_for_yoga(["Saturn"], dignity, "Distress to elders, trouble from enemies or weapons")
    assert r is not None
    assert r["theme"] == "saturn_affliction"


def test_remedy_for_yoga_negative_text_no_specific_malefic_falls_back_general():
    dignity = {"Moon": "neutral"}
    r = remedy_for_yoga(["Moon"], dignity, "Frequently loses fortune; mental grief, insignificant")
    assert r is not None
    assert r["theme"] == "general"


def test_priority_predictions_shape_for_real_chart():
    facts = build_report_facts(
        birth_datetime="1975-04-22T19:15:00",
        birth_lat=12.2979,
        birth_lon=76.6393,
        birth_tz=5.5,
    )
    pp = facts.get("priority_predictions")
    assert pp is not None
    assert 0 < len(pp) <= 6

    scores = [e["score"] for e in pp]
    assert scores == sorted(scores, reverse=True), "priority_predictions must be sorted by score descending"

    for entry in pp:
        assert entry["planets_involved"], "every surfaced entry must have known planets"
        assert entry["timing_windows"], "every surfaced entry must have at least one timing window"
        for w in entry["timing_windows"]:
            assert w["when"] in ("past", "current", "future")
            assert w["start"] <= w["end"]
        assert entry["manifestation_text"]
        # remedy is optional (None for positive/neutral yogas) but if present
        # must carry a theme + non-empty remedies list
        if entry["remedy"] is not None:
            assert entry["remedy"]["theme"]
            assert entry["remedy"]["remedies"]


def test_priority_predictions_empty_when_no_yogas_or_sav():
    from app.report_facts import _priority_predictions

    jd, place = jd_place(parse_dt("1975-04-22T19:15:00"), 12.2979, 76.6393, 5.5)
    assert _priority_predictions({}, [0] * 12, {}, [], jd, place, "2026-01-01") == []
    assert _priority_predictions({"x": {"planets": ["Sun"]}}, None, {}, [], jd, place, "2026-01-01") == []
