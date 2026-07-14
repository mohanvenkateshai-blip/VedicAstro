"""Person Timeline projection over canonical chart and legacy report facts.

This is a product projection, not a forecasting release mechanism.  Existing
``priority_predictions`` are migrated as engine inferences and remain visibly
non-prospective.  The projection preserves their native Mahadasha interval and
does not invent a peak, tolerance, probability, or event occurrence.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta, timezone
from typing import Any, Protocol
from urllib.parse import urlencode

import swisseph as swe
from app.dasha_vimshottari import running_ladder
from app.ephem import (
    ephemeris_runtime_provenance,
    jd_place,
    parse_dt,
    set_ayanamsa,
)
from app.report_facts import build_report_facts

from research_engine.identity import stable_hash

from .contracts import (
    DashaPeriod,
    EventDirection,
    EvidenceRole,
    MilestoneEvidenceLink,
    MilestoneOrigin,
    MilestoneProvenance,
    MilestoneResolution,
    PersonTimeline,
    SubjectProtection,
    SubjectReference,
    TemporalResolution,
    TemporalTolerance,
    TimelineMilestone,
    TimelineWindow,
    TimingLadder,
)
from .narration import (
    evidence_summary,
    legacy_candidate_statement,
    legacy_identity_notice,
    temporal_precision_text,
)
from .provenance import build_milestone, stable_timeline_id
from .store import SQLiteTimelineStore, TimelineStoreConflict

_ADAPTER_VERSION = "legacy-priority-prediction-timeline-v1"
_CALCULATION_METHOD = "report-priority-yoga-md-activation-v1"
_LEVEL_SLUG = {
    "Mahadasha": "md",
    "Antardasha": "ad",
    "Pratyantardasha": "pd",
    "Sookshma": "sd",
    "Prana": "prana",
}


class TimelineStoreReader(Protocol):
    def list_milestones(self, timeline_id: str) -> tuple[TimelineMilestone, ...]: ...

    def replay_milestone(self, milestone_id: str) -> TimelineMilestone: ...

    def list_current_resolutions(self, timeline_id: str) -> tuple[MilestoneResolution, ...]: ...


def subject_reference(subject_id: str) -> SubjectReference:
    """De-identify a portal-owned chart id before it crosses the timeline store."""

    digest = stable_hash({"subject_id": subject_id.strip()})
    return SubjectReference(
        reference_id=f"subj_{digest[:32]}",
        protection=SubjectProtection.DEIDENTIFIED,
    )


def timeline_id_for(subject: SubjectReference) -> str:
    return stable_timeline_id(subject.reference_id)


def _fixed_timezone(offset_hours: float) -> timezone:
    return timezone(timedelta(minutes=round(offset_hours * 60)))


def _date_boundary(value: str, tz: timezone, *, end: bool = False) -> datetime:
    parsed = datetime.strptime(value, "%Y-%m-%d").date()
    return datetime.combine(parsed, time.max if end else time.min, tzinfo=tz)


def _midpoint_jd(window: TimelineWindow) -> float:
    midpoint = window.start_at + (window.end_at - window.start_at) / 2
    utc = midpoint.astimezone(UTC)
    return swe.julday(
        utc.year,
        utc.month,
        utc.day,
        utc.hour + utc.minute / 60 + utc.second / 3600,
    )


def _deep_link(periods: list[dict[str, Any]]) -> str:
    params: dict[str, str] = {"system": "vimshottari"}
    for row in periods:
        slug = _LEVEL_SLUG.get(str(row.get("levelLabel")))
        if slug:
            params[slug] = str(row.get("lord", ""))
    if periods:
        params["at"] = str(periods[-1].get("start", ""))
    return f"/chart/dasha?{urlencode(params)}"


def _timing_ladder(jd: float, place: Any, window: TimelineWindow, tz: timezone) -> TimingLadder:
    rows = running_ladder(jd, place, query_jd=_midpoint_jd(window), depth=3)
    deep_link = _deep_link(rows)
    periods = tuple(
        DashaPeriod(
            level=str(row["levelLabel"]),
            ruler=str(row["lord"]),
            start_at=_date_boundary(str(row["start"]), tz),
            end_at=_date_boundary(str(row["end"]), tz, end=True),
            node_id="vimshottari:" + "/".join(str(item) for item in row.get("lords", [])),
            deep_link=deep_link,
        )
        for row in rows
    )
    return TimingLadder(system="Vimshottari", periods=periods)


class PersonTimelineService:
    def __init__(self, store: TimelineStoreReader | SQLiteTimelineStore | None = None) -> None:
        self.store = store

    def close(self) -> None:
        close = getattr(self.store, "close", None)
        if callable(close):
            close()

    def capture_observed_event(
        self,
        *,
        subject_id: str,
        event_id: str,
        canonical_event_id: str,
        original_label: str,
        title: str,
        description: str | None,
        direction: EventDirection,
        magnitude: Any | None,
        window: TimelineWindow,
        recorded_at: datetime,
        supersedes_milestone_id: str | None = None,
    ) -> dict[str, Any]:
        store = self._writable_store()
        subject = subject_reference(subject_id)
        timeline_id = timeline_id_for(subject)
        self._ensure_timeline(store, timeline_id, subject, recorded_at)
        milestone = build_milestone(
            timeline_id=timeline_id,
            subject_reference_id=subject.reference_id,
            origin=MilestoneOrigin.OBSERVED_EVENT,
            origin_record_id=event_id,
            canonical_event_id=canonical_event_id,
            original_label=original_label,
            title=title,
            description=description,
            direction=direction,
            magnitude=magnitude,
            window=window,
            created_at=recorded_at,
            supersedes_milestone_id=supersedes_milestone_id,
            provenance=MilestoneProvenance(actor_id=f"person:{subject.reference_id}"),
        )
        content_hash = store.append_milestone(milestone)
        return {
            "milestone": milestone.model_dump(mode="json"),
            "contentHash": content_hash,
            "appendOnly": True,
        }

    def append_resolution(
        self, *, subject_id: str, resolution: MilestoneResolution
    ) -> dict[str, Any]:
        store = self._writable_store()
        prediction = store.replay_milestone(resolution.prediction_milestone_id)
        expected_subject = subject_reference(subject_id)
        if prediction.subject_reference_id != expected_subject.reference_id:
            raise TimelineStoreConflict("prediction does not belong to this subject")
        content_hash = store.append_resolution(resolution)
        return {
            "resolution": resolution.model_dump(mode="json"),
            "contentHash": content_hash,
            "appendOnly": True,
            "predictionMutated": False,
        }

    def _writable_store(self) -> SQLiteTimelineStore:
        if not isinstance(self.store, SQLiteTimelineStore):
            raise RuntimeError("Person Timeline durable writes are unavailable")
        return self.store

    @staticmethod
    def _ensure_timeline(
        store: SQLiteTimelineStore,
        timeline_id: str,
        subject: SubjectReference,
        created_at: datetime,
    ) -> None:
        try:
            existing = store.replay_timeline(timeline_id)
        except KeyError:
            store.append_timeline(
                PersonTimeline(
                    timeline_id=timeline_id,
                    subject=subject,
                    created_at=created_at,
                    outcome_ledger_version="timeline-append-only-v1",
                )
            )
            return
        if existing.subject != subject:
            raise TimelineStoreConflict("timeline subject identity does not match")

    def query(
        self,
        *,
        subject_id: str,
        birth_datetime: str,
        birth_lat: float,
        birth_lon: float,
        birth_tz: float,
        ayanamsa: str = "LAHIRI",
        name: str | None = None,
        query_date: str | None = None,
        _detail_milestone_id: str | None = None,
    ) -> dict[str, Any]:
        generated_at = datetime.now(UTC)
        subject = subject_reference(subject_id)
        timeline_id = timeline_id_for(subject)
        timeline = PersonTimeline(
            timeline_id=timeline_id,
            subject=subject,
            created_at=generated_at,
            prediction_release_versions=(),
            outcome_ledger_version="timeline-append-only-v1",
        )
        replay_timeline = getattr(self.store, "replay_timeline", None)
        if callable(replay_timeline):
            try:
                timeline = replay_timeline(timeline_id)
            except KeyError:
                pass
        query_date = query_date or generated_at.date().isoformat()
        set_ayanamsa(ayanamsa)
        birth_dt = parse_dt(birth_datetime)
        jd, place = jd_place(birth_dt, birth_lat, birth_lon, birth_tz)
        facts = build_report_facts(
            birth_datetime=birth_datetime,
            birth_lat=birth_lat,
            birth_lon=birth_lon,
            birth_tz=birth_tz,
            ayanamsa=ayanamsa,
            name=name,
            query_date=query_date,
            include_dasha_tree=True,
            include_varshaphala=False,
        )
        input_snapshot = {
            "birth_datetime": birth_datetime,
            "birth_lat": birth_lat,
            "birth_lon": birth_lon,
            "birth_tz": birth_tz,
            "ayanamsa": ayanamsa,
        }
        input_hash = stable_hash(input_snapshot)
        tz = _fixed_timezone(birth_tz)
        candidates: list[TimelineMilestone] = []
        details: dict[str, dict[str, Any]] = {}
        for prediction in facts.get("priority_predictions") or []:
            for index, raw_window in enumerate(prediction.get("timing_windows") or []):
                milestone, detail = self._legacy_candidate(
                    timeline_id=timeline_id,
                    subject=subject,
                    prediction=prediction,
                    raw_window=raw_window,
                    window_index=index,
                    generated_at=generated_at,
                    input_hash=input_hash,
                    jd=jd,
                    place=place,
                    tz=tz,
                    ayanamsa=ayanamsa,
                    detail_target=_detail_milestone_id,
                )
                candidates.append(milestone)
                if detail:
                    details[milestone.milestone_id] = detail

        stored: tuple[TimelineMilestone, ...] = ()
        if self.store is not None:
            try:
                stored = tuple(self.store.list_milestones(timeline_id))
            except KeyError:
                stored = ()
        all_milestones = sorted(
            (*stored, *candidates), key=lambda item: (item.window.start_at, item.milestone_id)
        )
        resolutions: tuple[MilestoneResolution, ...] = ()
        list_resolutions = getattr(self.store, "list_current_resolutions", None)
        if callable(list_resolutions):
            resolutions = tuple(list_resolutions(timeline_id))
        timing_periods = self._timing_periods(facts, tz)
        return {
            "timeline": timeline.model_dump(mode="json"),
            "generatedAt": generated_at.isoformat(),
            "scientificIdentity": {
                "legacyCandidates": "engine_inference",
                "prospectivePredictionCount": sum(
                    item.origin is MilestoneOrigin.PROSPECTIVE_PREDICTION
                    for item in all_milestones
                ),
                "notice": legacy_identity_notice(),
            },
            "milestones": [item.model_dump(mode="json") for item in all_milestones],
            "timingPeriods": timing_periods,
            "outcomes": [
                {
                    "resolutionId": item.resolution_id,
                    "predictionMilestoneId": item.prediction_milestone_id,
                    "observedMilestoneId": item.observed_milestone_id,
                    "status": item.status.value,
                    "actualWindow": (
                        item.actual_window.model_dump(mode="json")
                        if item.actual_window is not None
                        else None
                    ),
                    "certainty": item.certainty,
                    "resolvedAt": item.resolved_at.isoformat(),
                    "supersedesResolutionId": item.supersedes_resolution_id,
                }
                for item in resolutions
            ],
            "calculation": {
                "inputSnapshotHash": input_hash,
                "ayanamsa": ayanamsa,
                "ephemeris": ephemeris_runtime_provenance(jd),
                "method": _CALCULATION_METHOD,
                "ruleScoreNotice": "Legacy rule scores are ranking weights, not probability.",
            },
            # Used only by ``detail`` in-process and removed at the HTTP boundary.
            "_details": details,
        }

    def detail(self, milestone_id: str, **query: Any) -> dict[str, Any]:
        result = self.query(**query, _detail_milestone_id=milestone_id)
        generated = result.pop("_details")
        if milestone_id in generated:
            return generated[milestone_id]
        if self.store is not None:
            try:
                milestone = self.store.replay_milestone(milestone_id)
            except KeyError as exc:
                raise KeyError(milestone_id) from exc
            expected_subject = subject_reference(str(query["subject_id"]))
            if (
                milestone.timeline_id != timeline_id_for(expected_subject)
                or milestone.subject_reference_id != expected_subject.reference_id
            ):
                raise KeyError(milestone_id)
            return self._stored_detail(milestone, result["calculation"])
        raise KeyError(milestone_id)

    def _legacy_candidate(
        self,
        *,
        timeline_id: str,
        subject: SubjectReference,
        prediction: dict[str, Any],
        raw_window: dict[str, Any],
        window_index: int,
        generated_at: datetime,
        input_hash: str,
        jd: float,
        place: Any,
        tz: timezone,
        ayanamsa: str,
        detail_target: str | None,
    ) -> tuple[TimelineMilestone, dict[str, Any]]:
        yoga_key = str(prediction.get("yoga_key") or "unknown-yoga")
        planet = str(raw_window.get("planet") or "unknown")
        origin_record_id = f"legacy-priority:{yoga_key}:{planet}:{window_index}"
        canonical_event_id = f"legacy.yoga_activation.{yoga_key}"
        milestone_id, identity_hash = TimelineMilestone.stable_identity(
            timeline_id=timeline_id,
            subject_reference_id=subject.reference_id,
            origin=MilestoneOrigin.ENGINE_INFERENCE,
            origin_record_id=origin_record_id,
            canonical_event_id=canonical_event_id,
        )
        window = TimelineWindow(
            start_at=_date_boundary(str(raw_window["start"]), tz),
            peak_at=None,
            end_at=_date_boundary(str(raw_window["end"]), tz, end=True),
            native_resolution=TemporalResolution.TECHNIQUE_NATIVE,
            native_resolution_label="Mahadasha activation interval",
            tolerance=TemporalTolerance(
                before_seconds=0,
                after_seconds=0,
                native_label="Full source Mahadasha interval; no narrower tolerance was produced",
            ),
        )
        score = prediction.get("score")
        native_score_refs = () if score is None else (f"legacy_rule_score:{score}",)
        calculation_hash = stable_hash(
            {
                "adapter": _ADAPTER_VERSION,
                "input_snapshot_hash": input_hash,
                "origin_record_id": origin_record_id,
                "window": window.model_dump(mode="json"),
                "rule_score": score,
            }
        )
        milestone = TimelineMilestone(
            milestone_id=milestone_id,
            timeline_id=timeline_id,
            subject_reference_id=subject.reference_id,
            origin=MilestoneOrigin.ENGINE_INFERENCE,
            origin_record_id=origin_record_id,
            origin_identity_hash=identity_hash,
            canonical_event_id=canonical_event_id,
            original_label=str(prediction.get("name") or yoga_key),
            title=f"{prediction.get('name') or yoga_key} — migrated research candidate",
            description=legacy_candidate_statement(prediction),
            direction=EventDirection.MIXED,
            magnitude=None,
            window=window,
            created_at=generated_at,
            native_score_refs=native_score_refs,
            provenance=MilestoneProvenance(
                actor_id="legacy-report-adapter",
                engine_version=_ADAPTER_VERSION,
                run_id=f"legacy-replay:{calculation_hash[:24]}",
                input_snapshot_hash=input_hash,
                calculation_hash=calculation_hash,
                rule_pack_versions={"method": _CALCULATION_METHOD},
                artifact_refs=(f"report.priority_predictions:{yoga_key}",),
            ),
        )
        if detail_target != milestone_id:
            return milestone, {}
        ladder = _timing_ladder(jd, place, window, tz)
        evidence = MilestoneEvidenceLink(
            evidence_link_id=f"evidence_{stable_hash({'milestone': milestone_id, 'role': 'activation'})[:32]}",
            milestone_id=milestone_id,
            technique_run_id=milestone.provenance.run_id or "legacy-replay",
            configuration_id=_CALCULATION_METHOD,
            rule_ids=(yoga_key,),
            role=EvidenceRole.ACTIVATION,
            timing_ladder=ladder,
            native_score_ref=native_score_refs[0] if native_score_refs else None,
            calculated_artifact_ref=f"report.priority_predictions:{yoga_key}",
            created_at=generated_at,
        )
        support = [
            {
                "role": "activation",
                "statement": (
                    f"The legacy report ranked {prediction.get('name') or yoga_key} and associated "
                    f"it with {planet}'s Mahadasha."
                ),
                "nativeScoreRef": evidence.native_score_ref,
                "ruleIds": list(evidence.rule_ids),
                "artifactRef": evidence.calculated_artifact_ref,
            }
        ]
        opposition: list[dict[str, Any]] = []
        deep_link = ladder.periods[-1].deep_link if ladder.periods else "/chart/dasha"
        detail = {
            "milestone": milestone.model_dump(mode="json"),
            "humanStatement": legacy_candidate_statement(prediction),
            "direction": milestone.direction.value,
            "scientificIdentity": {
                "origin": milestone.origin.value,
                "prospective": False,
                "notice": legacy_identity_notice(),
            },
            "temporalPrecision": {
                "interval": window.model_dump(mode="json"),
                "statement": temporal_precision_text(
                    start=window.start_at.isoformat(),
                    peak=None,
                    end=window.end_at.isoformat(),
                    native_resolution=window.native_resolution_label,
                    tolerance=window.tolerance.native_label,
                ),
            },
            "timingLadders": [ladder.model_dump(mode="json")],
            "dashaDeepLink": deep_link,
            "supportingEvidence": support,
            "opposingEvidence": opposition,
            "evidenceSummary": evidence_summary(support, opposition),
            "oppositionNotice": "No opposing-technique rows were captured by the legacy report adapter.",
            "calculationTrace": {
                "method": _CALCULATION_METHOD,
                "methodDescription": (
                    "Legacy yoga ranking used SAV, Shadbala and dignity components, then attached "
                    "the involved planet's Mahadasha. This is a research ranking, not a validated forecast."
                ),
                "inputSnapshotHash": input_hash,
                "calculationHash": calculation_hash,
                "replayRunId": milestone.provenance.run_id,
                "ayanamsa": ayanamsa,
                "ephemeris": ephemeris_runtime_provenance(jd),
                "nativeScoreRefs": list(native_score_refs),
                "scoreMeaning": "Rule-ranking score; not probability and not calibrated confidence.",
            },
        }
        return milestone, detail

    @staticmethod
    def _timing_periods(facts: dict[str, Any], tz: timezone) -> list[dict[str, Any]]:
        periods: list[dict[str, Any]] = []
        for md in ((facts.get("dashas") or {}).get("dashaTree") or []):
            md_rows = [
                {
                    "levelLabel": "Mahadasha",
                    "lord": md.get("lord"),
                    "lords": [md.get("lord")],
                    "start": md.get("start"),
                }
            ]
            periods.append(
                {
                    "system": "Vimshottari",
                    "level": "Mahadasha",
                    "ruler": md.get("lord"),
                    "startAt": _date_boundary(md["start"], tz).isoformat(),
                    "endAt": _date_boundary(md["end"], tz, end=True).isoformat(),
                    "deepLink": _deep_link(md_rows),
                }
            )
            for ad in md.get("subPeriods") or []:
                rows = [
                    *md_rows,
                    {
                        "levelLabel": "Antardasha",
                        "lord": ad.get("lord"),
                        "lords": [md.get("lord"), ad.get("lord")],
                        "start": ad.get("start"),
                    },
                ]
                periods.append(
                    {
                        "system": "Vimshottari",
                        "level": "Antardasha",
                        "ruler": ad.get("lord"),
                        "parentRuler": md.get("lord"),
                        "startAt": _date_boundary(ad["start"], tz).isoformat(),
                        "endAt": _date_boundary(ad["end"], tz, end=True).isoformat(),
                        "deepLink": _deep_link(rows),
                    }
                )
        return periods

    @staticmethod
    def _stored_detail(
        milestone: TimelineMilestone, calculation: dict[str, Any]
    ) -> dict[str, Any]:
        notice = (
            legacy_identity_notice()
            if milestone.origin is MilestoneOrigin.ENGINE_INFERENCE
            else "This record retains its declared origin and cannot be converted into a prospective prediction."
        )
        return {
            "milestone": milestone.model_dump(mode="json"),
            "humanStatement": milestone.description or milestone.title,
            "direction": milestone.direction.value,
            "scientificIdentity": {
                "origin": milestone.origin.value,
                "prospective": milestone.origin is MilestoneOrigin.PROSPECTIVE_PREDICTION,
                "notice": notice,
            },
            "temporalPrecision": {"interval": milestone.window.model_dump(mode="json")},
            "timingLadders": [],
            "dashaDeepLink": "/chart/dasha",
            "supportingEvidence": [],
            "opposingEvidence": [],
            "oppositionNotice": "No linked evidence rows are available in this projection.",
            "calculationTrace": {
                **calculation,
                "calculationHash": milestone.provenance.calculation_hash,
                "replayRunId": milestone.provenance.run_id,
            },
        }
