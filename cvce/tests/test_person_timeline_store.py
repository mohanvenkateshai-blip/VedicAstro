from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from research_engine.identity import stable_hash
from research_engine.timeline import (
    LinkRelation,
    MatchCriteria,
    MatchDisposition,
    MilestoneOrigin,
    MilestonePredictionLink,
    MilestoneProvenance,
    MilestoneResolution,
    PersonTimeline,
    ResolutionStatus,
    SQLiteTimelineStore,
    SubjectProtection,
    SubjectReference,
    TemporalResolution,
    TemporalTolerance,
    TimelineStoreConflict,
    TimelineWindow,
    build_milestone,
    match_milestones,
    stable_timeline_id,
    temporal_order_proof,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
SUBJECT = SubjectReference(
    reference_id="subj_0123456789abcdef", protection=SubjectProtection.DEIDENTIFIED
)
TIMELINE_ID = stable_timeline_id(SUBJECT.reference_id)
PROVENANCE = MilestoneProvenance(actor_id="test-engine", engine_version="1.0.0")


def window(start_days: int, end_days: int) -> TimelineWindow:
    return TimelineWindow(
        start_at=NOW + timedelta(days=start_days),
        peak_at=NOW + timedelta(days=(start_days + end_days) / 2),
        end_at=NOW + timedelta(days=end_days),
        native_resolution=TemporalResolution.DAY,
        native_resolution_label="day",
        tolerance=TemporalTolerance(
            before_seconds=86400, after_seconds=86400, native_label="plus or minus one day"
        ),
    )


def milestone(
    origin: MilestoneOrigin,
    origin_record_id: str,
    *,
    supersedes: str | None = None,
    created_at: datetime = NOW,
):
    values = {}
    if origin is MilestoneOrigin.PROSPECTIVE_PREDICTION:
        frozen_payload = criteria_payload()
        values = {
            "sealed_at": NOW,
            "knowledge_cutoff_at": NOW - timedelta(days=1),
            "sealed_match_criteria": frozen_payload,
            "sealed_match_criteria_hash": stable_hash(frozen_payload),
        }
    return build_milestone(
        timeline_id=TIMELINE_ID,
        subject_reference_id=SUBJECT.reference_id,
        origin=origin,
        origin_record_id=origin_record_id,
        canonical_event_id="career.role_change",
        original_label="Role change",
        title="Role change",
        window=window(30, 40),
        created_at=created_at,
        provenance=PROVENANCE,
        supersedes_milestone_id=supersedes,
        **values,
    )


def timeline() -> PersonTimeline:
    return PersonTimeline(timeline_id=TIMELINE_ID, subject=SUBJECT, created_at=NOW)


def criteria() -> MatchCriteria:
    return MatchCriteria.freeze(
        criteria_id="career-role-change-v1",
        version="1.0.0",
        canonical_event_id="career.role_change",
        minimum_overlap_ratio=0.3,
        partial_overlap_ratio=0.1,
    )


def criteria_payload(value: MatchCriteria | None = None) -> dict:
    return (value or criteria()).model_dump(mode="json", exclude={"criteria_hash"})


def prediction_link(prediction, observed, *, relation=LinkRelation.MATCHED, raw_id=None):
    frozen = criteria()
    values = {
        "milestone_id": observed.milestone_id,
        "prediction_milestone_id": prediction.milestone_id,
        "raw_prediction_id": raw_id or prediction.origin_record_id,
        "relation": relation,
        "match_method": "event-window-overlap",
        "match_version": "1.0.0",
        "criteria_hash": frozen.criteria_hash,
    }
    return MilestonePredictionLink(
        link_id=MilestonePredictionLink.stable_identity(**values),
        **values,
        prediction_origin=prediction.origin,
        temporal_order_proof=temporal_order_proof(
            prediction_created_at=prediction.created_at,
            prediction_sealed_at=prediction.sealed_at,
            outcome_known_at=observed.created_at,
        ),
        match_criteria=criteria_payload(frozen),
        created_at=observed.created_at,
    )


def test_origin_identity_is_stable_and_prospective_cannot_be_relabelled() -> None:
    first = milestone(MilestoneOrigin.PROSPECTIVE_PREDICTION, "release-claim-1")
    second = milestone(MilestoneOrigin.PROSPECTIVE_PREDICTION, "release-claim-1")
    assert first.milestone_id == second.milestone_id
    assert first.origin_identity_hash == second.origin_identity_hash

    payload = first.model_dump(mode="python")
    payload["origin"] = MilestoneOrigin.RETROSPECTIVE_HYPOTHESIS
    with pytest.raises(ValidationError, match="immutable origin identity"):
        type(first)(**payload)


def test_subject_reference_rejects_raw_or_unprotected_identity() -> None:
    with pytest.raises(ValidationError):
        SubjectReference(reference_id="Jane Doe 1990-01-01", protection=SubjectProtection.DEIDENTIFIED)
    with pytest.raises(ValidationError, match="key_id"):
        SubjectReference(reference_id="enc_abcdefghijklmnop", protection=SubjectProtection.ENCRYPTED)


def test_append_replay_correction_and_sealed_prediction_policy(tmp_path) -> None:
    with SQLiteTimelineStore(tmp_path / "timeline.sqlite") as store:
        store.append_timeline(timeline())
        observed = milestone(MilestoneOrigin.OBSERVED_EVENT, "user-event-1")
        prediction = milestone(MilestoneOrigin.PROSPECTIVE_PREDICTION, "release-claim-1")
        store.append_milestone(observed)
        store.append_milestone(prediction)
        corrected = milestone(
            MilestoneOrigin.OBSERVED_EVENT,
            "user-event-1-correction-1",
            supersedes=observed.milestone_id,
            created_at=NOW + timedelta(hours=1),
        )
        store.append_milestone(corrected)
        assert store.replay_milestone(corrected.milestone_id) == corrected

        attempted = milestone(
            MilestoneOrigin.PROSPECTIVE_PREDICTION,
            "release-claim-1-correction",
            supersedes=prediction.milestone_id,
            created_at=NOW,
        )
        with pytest.raises(TimelineStoreConflict, match="cannot be superseded"):
            store.append_milestone(attempted)


def test_replay_accepts_hash_valid_rows_from_before_optional_contract_fields(tmp_path) -> None:
    """Adding optional fields must not orphan an append-only historical ledger row."""

    with SQLiteTimelineStore(tmp_path / "timeline.sqlite") as store:
        store.append_timeline(timeline())
        observed = milestone(MilestoneOrigin.OBSERVED_EVENT, "legacy-user-event")
        raw = observed.model_dump(mode="json")
        raw.pop("sealed_match_criteria")
        raw.pop("sealed_match_criteria_hash")
        payload_json = json.dumps(raw, sort_keys=True, separators=(",", ":"))
        store._db.execute(  # noqa: SLF001 - explicit old-schema replay fixture
            "INSERT INTO timeline_milestones VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                observed.milestone_id,
                observed.timeline_id,
                observed.origin.value,
                observed.origin_identity_hash,
                None,
                observed.created_at.isoformat(),
                stable_hash(raw),
                payload_json,
            ),
        )
        store._db.commit()  # noqa: SLF001

        assert store.replay_milestone(observed.milestone_id) == observed


def test_resolutions_are_append_only_and_replay_current_successor(tmp_path) -> None:
    with SQLiteTimelineStore(tmp_path / "timeline.sqlite") as store:
        store.append_timeline(timeline())
        prediction = milestone(MilestoneOrigin.PROSPECTIVE_PREDICTION, "claim-1")
        observed = milestone(MilestoneOrigin.OBSERVED_EVENT, "event-1")
        store.append_milestone(prediction)
        store.append_milestone(observed)
        first = MilestoneResolution(
            resolution_id="resolution-1",
            prediction_milestone_id=prediction.milestone_id,
            observed_milestone_id=observed.milestone_id,
            status=ResolutionStatus.HIT,
            actual_window=observed.window,
            certainty="month known",
            resolver_id="user",
            resolved_at=NOW + timedelta(days=50),
            match_criteria=criteria_payload(),
        )
        second = first.model_copy(
            update={
                "resolution_id": "resolution-2",
                "status": ResolutionStatus.HIT,
                "resolved_at": NOW + timedelta(days=51),
                "supersedes_resolution_id": first.resolution_id,
            }
        )
        store.append_resolution(first)
        store.append_resolution(second)
        assert store.replay_resolution(first.resolution_id) == first
        assert store.current_resolution(prediction.milestone_id) == second


def test_matching_is_event_specific_and_tolerance_aware() -> None:
    prediction = milestone(MilestoneOrigin.PROSPECTIVE_PREDICTION, "claim-match")
    observed = build_milestone(
        timeline_id=TIMELINE_ID,
        subject_reference_id=SUBJECT.reference_id,
        origin=MilestoneOrigin.OBSERVED_EVENT,
        origin_record_id="event-match",
        canonical_event_id="career.role_change",
        original_label="Role change",
        title="Role change",
        window=window(40, 43),
        created_at=NOW + timedelta(days=44),
        provenance=PROVENANCE,
    )
    frozen = criteria()
    result = match_milestones(prediction, observed, frozen)
    assert result.disposition is MatchDisposition.MATCH
    assert result.criteria_hash == frozen.criteria_hash


def test_store_serializes_threaded_appends(tmp_path) -> None:
    with SQLiteTimelineStore(tmp_path / "timeline.sqlite") as store:
        store.append_timeline(timeline())
        records = [
            milestone(MilestoneOrigin.OBSERVED_EVENT, f"event-{index}") for index in range(12)
        ]
        with ThreadPoolExecutor(max_workers=4) as pool:
            hashes = tuple(pool.map(store.append_milestone, records))
        assert len(hashes) == 12
        assert len(store.list_milestones(TIMELINE_ID)) == 12


def test_temporal_order_proof_canonicalizes_offsets_and_link_replays(tmp_path) -> None:
    offset = timezone(timedelta(hours=5, minutes=30))
    shifted = temporal_order_proof(
        prediction_created_at=NOW.astimezone(offset),
        prediction_sealed_at=NOW.astimezone(offset),
        outcome_known_at=(NOW + timedelta(days=45)).astimezone(offset),
    )
    canonical = temporal_order_proof(
        prediction_created_at=NOW,
        prediction_sealed_at=NOW,
        outcome_known_at=NOW + timedelta(days=45),
    )
    assert shifted.proof_hash == canonical.proof_hash
    with pytest.raises(ValidationError, match="proof hash"):
        type(canonical)(
            prediction_created_at=canonical.prediction_created_at,
            prediction_sealed_at=canonical.prediction_sealed_at,
            outcome_known_at=canonical.outcome_known_at,
            proof_hash="0" * 64,
        )

    with SQLiteTimelineStore(tmp_path / "timeline.sqlite") as store:
        store.append_timeline(timeline())
        prediction = milestone(MilestoneOrigin.PROSPECTIVE_PREDICTION, "claim-link")
        observed = milestone(
            MilestoneOrigin.OBSERVED_EVENT,
            "event-link",
            created_at=NOW + timedelta(days=45),
        )
        store.append_milestone(prediction)
        store.append_milestone(observed)
        link = prediction_link(prediction, observed)
        store.append_prediction_link(link)
        assert store.replay_prediction_link(link.link_id) == link


def test_prediction_link_rejects_raw_binding_relation_and_arbitrary_identity(tmp_path) -> None:
    prediction = milestone(MilestoneOrigin.PROSPECTIVE_PREDICTION, "claim-binding")
    observed = milestone(
        MilestoneOrigin.OBSERVED_EVENT,
        "event-binding",
        created_at=NOW + timedelta(days=45),
    )
    with pytest.raises(ValidationError, match="stable prediction-link identity"):
        MilestonePredictionLink.model_validate(
            {**prediction_link(prediction, observed).model_dump(), "link_id": "arbitrary"}
        )
    valid_payload = prediction_link(prediction, observed).model_dump()
    with pytest.raises(ValidationError, match="criteria_hash"):
        MilestonePredictionLink.model_validate(
            {**valid_payload, "criteria_hash": "0" * 64, "link_id": "tmlink_" + "0" * 32}
        )

    with SQLiteTimelineStore(tmp_path / "timeline.sqlite") as store:
        store.append_timeline(timeline())
        store.append_milestone(prediction)
        store.append_milestone(observed)
        with pytest.raises(TimelineStoreConflict, match="raw prediction id"):
            store.append_prediction_link(prediction_link(prediction, observed, raw_id="invented"))
        with pytest.raises(TimelineStoreConflict, match="contradicts"):
            store.append_prediction_link(
                prediction_link(prediction, observed, relation=LinkRelation.UNRELATED)
            )


def test_resolution_rejects_false_hit_timing_and_early_knowledge(tmp_path) -> None:
    prediction = milestone(MilestoneOrigin.PROSPECTIVE_PREDICTION, "claim-resolution-policy")
    observed = milestone(
        MilestoneOrigin.OBSERVED_EVENT,
        "event-resolution-policy",
        created_at=NOW + timedelta(days=45),
    )
    base = dict(
        prediction_milestone_id=prediction.milestone_id,
        observed_milestone_id=observed.milestone_id,
        status=ResolutionStatus.HIT,
        actual_window=observed.window,
        certainty="exact",
        resolver_id="user",
        match_criteria=criteria_payload(),
    )
    with SQLiteTimelineStore(tmp_path / "timeline.sqlite") as store:
        store.append_timeline(timeline())
        store.append_milestone(prediction)
        store.append_milestone(observed)
        early = MilestoneResolution(
            resolution_id="early", resolved_at=NOW + timedelta(days=44), **base
        )
        with pytest.raises(TimelineStoreConflict, match="predate"):
            store.append_resolution(early)
        wrong_window = MilestoneResolution(
            resolution_id="wrong-window",
            resolved_at=NOW + timedelta(days=46),
            **{**base, "actual_window": window(31, 40)},
        )
        with pytest.raises(TimelineStoreConflict, match="actual interval"):
            store.append_resolution(wrong_window)
        wrong_event = build_milestone(
            timeline_id=TIMELINE_ID,
            subject_reference_id=SUBJECT.reference_id,
            origin=MilestoneOrigin.OBSERVED_EVENT,
            origin_record_id="different-event",
            canonical_event_id="relationship.marriage",
            original_label="Marriage",
            title="Marriage",
            window=prediction.window,
            created_at=NOW + timedelta(days=45),
            provenance=PROVENANCE,
        )
        store.append_milestone(wrong_event)
        false_hit = MilestoneResolution(
            resolution_id="false-hit",
            resolved_at=NOW + timedelta(days=46),
            **{
                **base,
                "observed_milestone_id": wrong_event.milestone_id,
                "actual_window": wrong_event.window,
            },
        )
        with pytest.raises(TimelineStoreConflict, match="matcher result"):
            store.append_resolution(false_hit)
        tailored = criteria_payload()
        tailored["minimum_overlap_ratio"] = 0.1
        tailored_resolution = MilestoneResolution(
            resolution_id="tailored-after-outcome",
            resolved_at=NOW + timedelta(days=46),
            **{**base, "match_criteria": tailored},
        )
        with pytest.raises(TimelineStoreConflict, match="differ from the sealed"):
            store.append_resolution(tailored_resolution)
        for status in (ResolutionStatus.MISS, ResolutionStatus.FALSE_ALARM):
            premature = MilestoneResolution(
                resolution_id=f"premature-{status.value}",
                prediction_milestone_id=prediction.milestone_id,
                status=status,
                certainty="certain",
                resolver_id="user",
                resolved_at=NOW + timedelta(days=35),
            )
            with pytest.raises(TimelineStoreConflict, match="before the prediction window ends"):
                store.append_resolution(premature)


def test_prospective_prediction_requires_immutable_seal_time_criteria() -> None:
    valid = milestone(MilestoneOrigin.PROSPECTIVE_PREDICTION, "sealed-criteria-required")
    payload = valid.model_dump(mode="python")
    payload["sealed_match_criteria"] = None
    payload["sealed_match_criteria_hash"] = None
    with pytest.raises(ValidationError, match="seal-time matching criteria"):
        type(valid)(**payload)

    payload = valid.model_dump(mode="python")
    payload["sealed_match_criteria"]["minimum_overlap_ratio"] = 0.99
    with pytest.raises(ValidationError, match="criteria hash"):
        type(valid)(**payload)


def test_resolution_history_has_one_root_and_no_forks(tmp_path) -> None:
    with SQLiteTimelineStore(tmp_path / "timeline.sqlite") as store:
        store.append_timeline(timeline())
        prediction = milestone(MilestoneOrigin.PROSPECTIVE_PREDICTION, "claim-chain")
        observed = milestone(
            MilestoneOrigin.OBSERVED_EVENT, "event-chain", created_at=NOW + timedelta(days=45)
        )
        store.append_milestone(prediction)
        store.append_milestone(observed)
        base = dict(
            prediction_milestone_id=prediction.milestone_id,
            observed_milestone_id=observed.milestone_id,
            status=ResolutionStatus.HIT,
            actual_window=observed.window,
            certainty="exact",
            resolver_id="user",
            match_criteria=criteria_payload(),
        )
        root = MilestoneResolution(
            resolution_id="root", resolved_at=NOW + timedelta(days=46), **base
        )
        store.append_resolution(root)
        with pytest.raises(TimelineStoreConflict):
            store.append_resolution(
                MilestoneResolution(
                    resolution_id="second-root", resolved_at=NOW + timedelta(days=47), **base
                )
            )
        child = MilestoneResolution(
            resolution_id="child",
            resolved_at=NOW + timedelta(days=47),
            supersedes_resolution_id="root",
            **base,
        )
        store.append_resolution(child)
        with pytest.raises(TimelineStoreConflict):
            store.append_resolution(
                MilestoneResolution(
                    resolution_id="fork",
                    resolved_at=NOW + timedelta(days=48),
                    supersedes_resolution_id="root",
                    **base,
                )
            )


def test_matcher_handles_instants_and_rejects_cross_subject_or_timeline() -> None:
    instant_window = TimelineWindow(
        start_at=NOW + timedelta(days=35),
        peak_at=NOW + timedelta(days=35),
        end_at=NOW + timedelta(days=35),
        native_resolution=TemporalResolution.INSTANT,
        native_resolution_label="exact trigger",
        tolerance=TemporalTolerance(before_seconds=0, after_seconds=0, native_label="exact"),
    )
    prediction = build_milestone(
        timeline_id=TIMELINE_ID,
        subject_reference_id=SUBJECT.reference_id,
        origin=MilestoneOrigin.PROSPECTIVE_PREDICTION,
        origin_record_id="instant-claim",
        canonical_event_id="career.role_change",
        original_label="Role change",
        title="Role change",
        window=instant_window,
        created_at=NOW,
        sealed_at=NOW,
        knowledge_cutoff_at=NOW,
        sealed_match_criteria=criteria_payload(),
        sealed_match_criteria_hash=stable_hash(criteria_payload()),
        provenance=PROVENANCE,
    )
    observed = build_milestone(
        timeline_id=TIMELINE_ID,
        subject_reference_id=SUBJECT.reference_id,
        origin=MilestoneOrigin.OBSERVED_EVENT,
        origin_record_id="instant-event",
        canonical_event_id="career.role_change",
        original_label="Role change",
        title="Role change",
        window=instant_window,
        created_at=NOW + timedelta(days=36),
        provenance=PROVENANCE,
    )
    assert match_milestones(prediction, observed, criteria()).disposition is MatchDisposition.MATCH
    foreign = observed.model_copy(update={"timeline_id": "different-timeline"})
    with pytest.raises(ValueError, match="same timeline"):
        match_milestones(prediction, foreign, criteria())
    foreign_subject = observed.model_copy(update={"subject_reference_id": "subj_fedcba9876543210"})
    with pytest.raises(ValueError, match="same protected subject"):
        match_milestones(prediction, foreign_subject, criteria())
