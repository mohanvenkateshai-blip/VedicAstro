from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app import server
from fastapi.testclient import TestClient
from research_engine.identity import stable_hash
from research_engine.timeline import (
    EventDirection,
    MilestoneOrigin,
    MilestoneProvenance,
    TemporalResolution,
    TemporalTolerance,
    TimelineWindow,
    build_milestone,
)
from research_engine.timeline import service as timeline_service
from research_engine.timeline.service import PersonTimelineService

client = TestClient(server.app)


@pytest.fixture(autouse=True)
def timeline_configuration(monkeypatch, tmp_path):
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", "")
    monkeypatch.setattr(server.settings, "SERVICE_AUTH_REQUIRED", False)
    monkeypatch.setattr(server.settings, "TIMELINE_DB_PATH", str(tmp_path / "timeline.sqlite3"))
    monkeypatch.setattr(server.settings, "TIMELINE_WRITES_ENABLED", True)
    server._clear_timeline_service_cache()
    server._rate_limit_store.clear()
    yield
    server._clear_timeline_service_cache()
    server._rate_limit_store.clear()


@pytest.fixture
def legacy_facts(monkeypatch):
    facts = {
        "priority_predictions": [
            {
                "yoga_key": "harsha_yoga",
                "name": "Harsha Yoga",
                "score": 64.42,
                "planets_involved": ["Jupiter"],
                "timing_windows": [
                    {
                        "planet": "Jupiter",
                        "start": "2020-11-28",
                        "end": "2036-11-28",
                        "when": "current",
                    }
                ],
                "manifestation_text": "A broad legacy manifestation statement.",
                "remedy": None,
            }
        ],
        "dashas": {
            "dashaTree": [
                {
                    "lord": "Jupiter",
                    "start": "2020-11-28",
                    "end": "2036-11-28",
                    "subPeriods": [
                        {
                            "lord": "Mercury",
                            "start": "2025-07-29",
                            "end": "2027-11-04",
                        }
                    ],
                }
            ]
        },
    }
    monkeypatch.setattr(timeline_service, "build_report_facts", lambda **_: facts)
    monkeypatch.setattr(
        timeline_service,
        "running_ladder",
        lambda *_args, **_kwargs: [
            {
                "levelLabel": "Mahadasha",
                "lord": "Jupiter",
                "lords": ["Jupiter"],
                "start": "2020-11-28",
                "end": "2036-11-28",
            },
            {
                "levelLabel": "Antardasha",
                "lord": "Mercury",
                "lords": ["Jupiter", "Mercury"],
                "start": "2025-07-29",
                "end": "2027-11-04",
            },
            {
                "levelLabel": "Pratyantardasha",
                "lord": "Moon",
                "lords": ["Jupiter", "Mercury", "Moon"],
                "start": "2026-07-09",
                "end": "2026-09-16",
            },
        ],
    )
    monkeypatch.setattr(
        timeline_service,
        "ephemeris_runtime_provenance",
        lambda _jd: {"engine": "PyJHora", "backend": "Swiss Ephemeris"},
    )
    return facts


def birth_payload() -> dict:
    return {
        "subject_id": "chart-fixture-1",
        "birth_datetime": "1975-04-22T19:15:00",
        "birth_lat": 12.2979,
        "birth_lon": 76.6393,
        "birth_tz": 5.5,
        "ayanamsa": "LAHIRI",
        "query_date": "2026-07-14",
    }


def event_payload() -> dict:
    return {
        "subject_id": "chart-fixture-1",
        "event_id": "person-event-1",
        "canonical_event_id": "life.career.role_change",
        "title": "Changed role",
        "description": "Moved to a different role.",
        "direction": "mixed",
        "window": {
            "start_at": "2024-03-01T00:00:00+05:30",
            "peak_at": "2024-03-15T12:00:00+05:30",
            "end_at": "2024-03-31T23:59:59+05:30",
            "native_resolution": "month",
            "native_resolution_label": "month remembered by the person",
            "tolerance": {
                "before_seconds": 0,
                "after_seconds": 0,
                "native_label": "month-level recollection",
            },
        },
        "recorded_at": "2026-07-14T12:00:00Z",
    }


def test_legacy_candidate_direction_reflects_yoga_polarity(monkeypatch):
    facts = {
        "priority_predictions": [
            {
                "yoga_key": "favourable_yoga",
                "name": "Favourable Yoga",
                "score": 80.0,
                "planets_involved": ["Jupiter"],
                "timing_windows": [
                    {
                        "planet": "Jupiter",
                        "start": "2020-11-28",
                        "end": "2036-11-28",
                        "when": "current",
                    }
                ],
                "manifestation_text": "A favourable legacy manifestation statement.",
                "remedy": None,
                "direction": "favourable",
            },
            {
                "yoga_key": "unfavourable_yoga",
                "name": "Unfavourable Yoga",
                "score": 60.0,
                "planets_involved": ["Saturn"],
                "timing_windows": [
                    {
                        "planet": "Saturn",
                        "start": "2010-01-01",
                        "end": "2029-01-01",
                        "when": "current",
                    }
                ],
                "manifestation_text": "An unfavourable legacy manifestation statement.",
                "remedy": None,
                "direction": "unfavourable",
            },
            {
                "yoga_key": "unlabelled_yoga",
                "name": "Unlabelled Yoga",
                "score": 40.0,
                "planets_involved": ["Mars"],
                "timing_windows": [
                    {
                        "planet": "Mars",
                        "start": "2005-01-01",
                        "end": "2050-01-01",
                        "when": "current",
                    }
                ],
                "manifestation_text": "An unlabelled legacy manifestation statement.",
                "remedy": None,
                # no "direction" key at all -> should fall back to mixed
            },
        ],
        "dashas": {"dashaTree": []},
    }
    monkeypatch.setattr(timeline_service, "build_report_facts", lambda **_: facts)
    monkeypatch.setattr(timeline_service, "running_ladder", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        timeline_service,
        "ephemeris_runtime_provenance",
        lambda _jd: {"engine": "PyJHora", "backend": "Swiss Ephemeris"},
    )

    result = PersonTimelineService().query(**birth_payload())
    by_yoga = {m["origin_record_id"].split(":")[1]: m for m in result["milestones"]}

    assert by_yoga["favourable_yoga"]["direction"] == "favourable"
    assert by_yoga["unfavourable_yoga"]["direction"] == "unfavourable"
    assert by_yoga["unlabelled_yoga"]["direction"] == "mixed"


def test_service_marks_legacy_candidates_as_non_prospective_and_preserves_precision(
    legacy_facts,
):
    result = PersonTimelineService().query(**birth_payload())
    milestone = result["milestones"][0]

    assert milestone["origin"] == "engine_inference"
    assert "migrated research candidate" in milestone["title"]
    assert milestone["window"]["peak_at"] is None
    assert milestone["window"]["native_resolution_label"] == "Mahadasha activation interval"
    assert milestone["native_score_refs"] == ["legacy_rule_score:64.42"]
    assert "not a prospective prediction" in result["scientificIdentity"]["notice"]
    assert "probability" in result["calculation"]["ruleScoreNotice"]


def test_timeline_query_and_detail_expose_md_ad_pd_and_evidence(legacy_facts):
    query = client.post("/timeline/query", json=birth_payload())
    assert query.status_code == 200, query.text
    body = query.json()
    assert "_details" not in body
    milestone_id = body["milestones"][0]["milestone_id"]

    detail = client.post(
        f"/timeline/milestones/{milestone_id}/detail", json=birth_payload()
    )
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert [row["level"] for row in payload["timingLadders"][0]["periods"]] == [
        "Mahadasha",
        "Antardasha",
        "Pratyantardasha",
    ]
    assert payload["supportingEvidence"]
    assert payload["opposingEvidence"] == []
    assert payload["dashaDeepLink"].startswith("/chart/dasha?")
    assert payload["calculationTrace"]["scoreMeaning"].startswith("Rule-ranking score")


def test_stored_detail_is_not_disclosed_to_a_different_subject(legacy_facts):
    created = client.post("/timeline/events", json=event_payload())
    assert created.status_code == 201
    milestone_id = created.json()["milestone"]["milestone_id"]
    other_subject = birth_payload()
    other_subject["subject_id"] = "chart-fixture-2"

    response = client.post(
        f"/timeline/milestones/{milestone_id}/detail", json=other_subject
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Timeline milestone not found"


def test_observed_event_is_appended_and_appears_in_person_timeline(legacy_facts):
    created = client.post("/timeline/events", json=event_payload())
    assert created.status_code == 201, created.text
    assert created.json()["appendOnly"] is True
    assert created.json()["milestone"]["origin"] == "observed_event"

    queried = client.post("/timeline/query", json=birth_payload())
    origins = {item["origin"] for item in queried.json()["milestones"]}
    assert origins == {"observed_event", "engine_inference"}

    duplicate = client.post("/timeline/events", json=event_payload())
    assert duplicate.status_code == 409

    observed_id = created.json()["milestone"]["milestone_id"]
    invalid_resolution = client.post(
        f"/timeline/milestones/{observed_id}/resolutions",
        json={
            "subject_id": "chart-fixture-1",
            "resolution_id": "resolution-observed-invalid",
            "status": "miss",
            "certainty": "certain",
            "resolver_id": "person",
            "resolved_at": "2026-07-14T13:00:00Z",
        },
    )
    assert invalid_resolution.status_code == 409
    assert "only sealed prospective predictions" in invalid_resolution.json()["detail"]


def test_timeline_writes_fail_closed_and_malformed_requests_are_422(monkeypatch):
    monkeypatch.setattr(server.settings, "TIMELINE_WRITES_ENABLED", False)
    assert client.post("/timeline/events", json=event_payload()).status_code == 503

    malformed = birth_payload()
    malformed["birth_datetime"] = "not-a-date"
    assert client.post("/timeline/query", json=malformed).status_code == 422


def test_timeline_endpoints_use_product_service_auth(monkeypatch, legacy_facts):
    monkeypatch.setattr(server.settings, "SERVICE_TOKEN", "timeline-secret")
    monkeypatch.setattr(server.settings, "SERVICE_AUTH_REQUIRED", True)
    assert client.post("/timeline/query", json=birth_payload()).status_code == 401
    accepted = client.post(
        "/timeline/query",
        headers={"x-cvce-service-token": "timeline-secret"},
        json=birth_payload(),
    )
    assert accepted.status_code == 200


def test_resolution_returns_404_for_unknown_prediction():
    response = client.post(
        "/timeline/milestones/not-stored/resolutions",
        json={
            "subject_id": "chart-fixture-1",
            "resolution_id": "resolution-1",
            "status": "miss",
            "certainty": "certain",
            "resolver_id": "person",
            "resolved_at": datetime(2026, 7, 14, 12, tzinfo=UTC).isoformat(),
        },
    )
    assert response.status_code == 404


def test_resolution_endpoint_appends_without_mutating_sealed_prediction(legacy_facts):
    observed_response = client.post("/timeline/events", json=event_payload())
    assert observed_response.status_code == 201
    observed = observed_response.json()["milestone"]
    service = server._get_timeline_service()
    store = service.store
    assert store is not None

    prediction_window = TimelineWindow(
        start_at=datetime(2024, 3, 1, tzinfo=UTC),
        peak_at=datetime(2024, 3, 15, tzinfo=UTC),
        end_at=datetime(2024, 3, 31, 23, 59, tzinfo=UTC),
        native_resolution=TemporalResolution.MONTH,
        native_resolution_label="month",
        tolerance=TemporalTolerance(native_label="calendar month"),
    )
    prediction = build_milestone(
        timeline_id=observed["timeline_id"],
        subject_reference_id=observed["subject_reference_id"],
        origin=MilestoneOrigin.PROSPECTIVE_PREDICTION,
        origin_record_id="sealed-forecast-1",
        canonical_event_id="life.career.role_change",
        original_label="Role change",
        title="A role change may occur",
        direction=EventDirection.MIXED,
        window=prediction_window,
        created_at=datetime(2023, 12, 1, tzinfo=UTC),
        sealed_at=datetime(2023, 12, 2, tzinfo=UTC),
        knowledge_cutoff_at=datetime(2023, 11, 30, tzinfo=UTC),
        sealed_match_criteria={
            "criteria_id": "career-role-change-v1",
            "version": "1.0.0",
            "canonical_event_id": "life.career.role_change",
            "accepted_event_ids": [],
            "require_peak_within_actual": False,
            "minimum_overlap_ratio": 0.3,
            "allow_tolerance": True,
            "partial_overlap_ratio": 0.0,
        },
        sealed_match_criteria_hash=stable_hash(
            {
                "criteria_id": "career-role-change-v1",
                "version": "1.0.0",
                "canonical_event_id": "life.career.role_change",
                "accepted_event_ids": [],
                "require_peak_within_actual": False,
                "minimum_overlap_ratio": 0.3,
                "allow_tolerance": True,
                "partial_overlap_ratio": 0.0,
            }
        ),
        provenance=MilestoneProvenance(
            actor_id="forecast-engine",
            run_id="sealed-run-1",
            release_id="sealed-release-1",
        ),
    )
    store.append_milestone(prediction)
    before = store.replay_milestone(prediction.milestone_id)

    response = client.post(
        f"/timeline/milestones/{prediction.milestone_id}/resolutions",
        json={
            "subject_id": "chart-fixture-1",
            "resolution_id": "resolution-hit-1",
            "observed_milestone_id": observed["milestone_id"],
            "status": "hit",
            "actual_window": event_payload()["window"],
            "certainty": "month confirmed",
            "resolver_id": "person",
            "resolved_at": "2026-07-14T13:00:00Z",
            "notes": ["Confirmed by the person."],
            "match_criteria": {
                "criteria_id": "career-role-change-v1",
                "version": "1.0.0",
                "canonical_event_id": "life.career.role_change",
                "minimum_overlap_ratio": 0.3,
            },
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["appendOnly"] is True
    assert response.json()["predictionMutated"] is False
    assert store.replay_milestone(prediction.milestone_id) == before

    timeline = client.post("/timeline/query", json=birth_payload())
    assert timeline.status_code == 200, timeline.text
    assert timeline.json()["outcomes"] == [
        {
            "resolutionId": "resolution-hit-1",
            "predictionMilestoneId": prediction.milestone_id,
            "observedMilestoneId": observed["milestone_id"],
            "status": "hit",
            "actualWindow": event_payload()["window"],
            "certainty": "month confirmed",
            "resolvedAt": "2026-07-14T13:00:00+00:00",
            "supersedesResolutionId": None,
        }
    ]
