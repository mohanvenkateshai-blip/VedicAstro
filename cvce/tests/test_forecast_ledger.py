from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime

import pytest
from forecasting import (
    Abstention,
    AbstentionCode,
    BirthTimeSensitivity,
    CalculationProvenance,
    CertaintyTier,
    ConsentAction,
    ConsentRecord,
    ConsentRequiredError,
    ForecastClaim,
    ForecastMode,
    ForecastPolarity,
    ForecastResolution,
    ImmutableLedgerError,
    LedgerDisabledError,
    ModelRelease,
    OutcomeObservation,
    OutcomeStatus,
    ProbabilityStatus,
    SQLiteForecastLedger,
    SubjectErasedError,
    TemporalGranularity,
    TimingWindow,
    UncertaintyAssessment,
    get_event_definition,
)
from forecasting.canonical import stable_hash
from forecasting.taxonomy import EventCode

TENANT_A = "tenant-a"
TENANT_B = "tenant-b"
SUBJECT = "subj_0e4f783ab19c44f1"
NOW = datetime(2027, 1, 10, 12, tzinfo=UTC)


def release() -> ModelRelease:
    manifest = {
        "engine_version": "cvce-ledger-test",
        "rule_packs": {"vimshottari": "1.0.0"},
        "contract_version": "1.0.0",
    }
    return ModelRelease(
        release_id="release-ledger-1",
        created_at=datetime(2027, 1, 1, tzinfo=UTC),
        manifest=manifest,
        manifest_hash=stable_hash(manifest),
    )


def claim(*, abstained: bool = False) -> ForecastClaim:
    event = get_event_definition(EventCode.CONTRACT_SIGNED)
    return ForecastClaim(
        claim_id="claim-ledger-1",
        forecast_id="forecast-ledger-1",
        release_id="release-ledger-1",
        locale="en-IN",
        mode=ForecastMode.FORECAST,
        event_code=event.code,
        event_domain=event.domain,
        observable_outcome=event.observable_predicate,
        timing=TimingWindow(
            start_on=date(2027, 2, 1),
            end_on=date(2027, 2, 28),
            resolution_due_on=date(2027, 3, 31),
            timezone="Europe/Dublin",
            granularity=TemporalGranularity.MONTH,
            horizon_days=28,
        ),
        polarity=ForecastPolarity.INDETERMINATE if abstained else ForecastPolarity.FAVOURABLE,
        traditional_strength_index=0 if abstained else 4.5,
        probability_status=ProbabilityStatus.UNAVAILABLE if abstained else ProbabilityStatus.UNCALIBRATED_SIGNAL,
        provenance=CalculationProvenance(
            calculation_hash="a" * 64,
            engine_version="cvce-ledger-test",
            rule_pack_versions={"vimshottari": "1.0.0"},
            data_cutoff_at=datetime(2027, 1, 8, tzinfo=UTC),
            calculated_at=datetime(2027, 1, 9, tzinfo=UTC),
        ),
        uncertainty=UncertaintyAssessment(
            birth_time_sensitivity=BirthTimeSensitivity.STABLE,
            data_completeness_ratio=0.9,
        ),
        what_to_expect=("A named agreement may reach signature stage.",),
        decision_scope="Do not substitute this signal for legal review.",
        limitations=("This traditional signal is not empirically calibrated.",),
        certainty_tier=CertaintyTier.INSUFFICIENT_EVIDENCE if abstained else CertaintyTier.TRADITIONAL_SIGNAL,
        abstention=Abstention(
            abstained=abstained,
            code=AbstentionCode.INSUFFICIENT_EVIDENCE if abstained else AbstentionCode.NONE,
            reason="Evidence did not meet issuance policy." if abstained else None,
        ),
    )


def consent(action: ConsentAction, *, event_id: str, at: datetime, reason: str | None = None) -> ConsentRecord:
    return ConsentRecord(
        event_id=event_id,
        consent_id="consent-v1",
        tenant_id=TENANT_A,
        subject_key=SUBJECT,
        action=action,
        purposes=("outcome_research",),
        occurred_at=at,
        reason=reason,
    )


def resolution(*, resolution_id: str = "resolution-1", supersedes: str | None = None) -> ForecastResolution:
    return ForecastResolution(
        resolution_id=resolution_id,
        claim_id="claim-ledger-1",
        tenant_id=TENANT_A,
        subject_key=SUBJECT,
        observation=OutcomeObservation(
            observation_id=f"observation-{resolution_id}",
            status=OutcomeStatus.DID_NOT_OCCUR,
            observed_at=datetime(2027, 3, 1, tzinfo=UTC),
            source="consented subject follow-up",
        ),
        recorded_at=datetime(2027, 3, 2, tzinfo=UTC),
        supersedes_resolution_id=supersedes,
    )


def prepared_ledger(tmp_path, *, outcomes: bool = True) -> SQLiteForecastLedger:
    tmp_path.mkdir(parents=True, exist_ok=True)
    ledger = SQLiteForecastLedger(tmp_path / "forecast-ledger.sqlite", outcome_writes_enabled=outcomes)
    ledger.register_release(release())
    ledger.issue_forecast(TENANT_A, SUBJECT, claim(), issued_at=NOW, rendered_content="A contract may be signed in February.")
    return ledger


def test_snapshot_replay_is_deterministic_and_immutable(tmp_path):
    ledger = prepared_ledger(tmp_path)
    assert ledger.replay_claim(TENANT_A, SUBJECT, "claim-ledger-1") == claim()

    with pytest.raises(ImmutableLedgerError):
        ledger.issue_forecast(TENANT_A, SUBJECT, claim(), issued_at=NOW, rendered_content="Changed wording")
    with pytest.raises(ImmutableLedgerError):
        ledger.replace_claim(claim())
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        ledger._db.execute("UPDATE issued_forecasts SET content_hash='tampered'")  # noqa: SLF001


def test_outcome_requires_feature_flag_and_active_consent(tmp_path):
    disabled = prepared_ledger(tmp_path / "disabled", outcomes=False)
    disabled.append_consent(consent(ConsentAction.GRANTED, event_id="grant-1", at=NOW))
    with pytest.raises(LedgerDisabledError):
        disabled.append_resolution("resolution-event-1", resolution())

    enabled = prepared_ledger(tmp_path / "enabled")
    with pytest.raises(ConsentRequiredError):
        enabled.append_resolution("resolution-event-1", resolution())
    enabled.append_consent(consent(ConsentAction.GRANTED, event_id="grant-1", at=NOW))
    enabled.append_resolution("resolution-event-1", resolution())
    assert len(enabled.export_subject(TENANT_A, SUBJECT).resolutions) == 1


def test_consent_withdrawal_blocks_future_outcomes_without_rewriting_history(tmp_path):
    ledger = prepared_ledger(tmp_path)
    ledger.append_consent(consent(ConsentAction.GRANTED, event_id="grant-1", at=NOW))
    ledger.append_resolution("resolution-event-1", resolution())
    ledger.append_consent(
        consent(
            ConsentAction.WITHDRAWN,
            event_id="withdraw-1",
            at=datetime(2027, 3, 3, tzinfo=UTC),
            reason="Participant withdrew research permission.",
        )
    )
    with pytest.raises(ConsentRequiredError):
        ledger.append_resolution("resolution-event-2", resolution(resolution_id="resolution-2"))
    assert len(ledger.export_subject(TENANT_A, SUBJECT).resolutions) == 1


def test_resolution_correction_appends_supersession_instead_of_overwriting(tmp_path):
    ledger = prepared_ledger(tmp_path)
    ledger.append_consent(consent(ConsentAction.GRANTED, event_id="grant-1", at=NOW))
    ledger.append_resolution("resolution-event-1", resolution())
    ledger.append_resolution(
        "resolution-event-2",
        resolution(resolution_id="resolution-2", supersedes="resolution-1"),
    )
    exported = ledger.export_subject(TENANT_A, SUBJECT)
    assert len(exported.resolutions) == 2
    assert exported.resolutions[-1]["supersedes_resolution_id"] == "resolution-1"


def test_tenant_subject_isolation_and_erasure_tombstone(tmp_path):
    ledger = prepared_ledger(tmp_path)
    assert ledger.export_subject(TENANT_B, SUBJECT).forecasts == ()
    with pytest.raises(KeyError):
        ledger.replay_claim(TENANT_B, SUBJECT, "claim-ledger-1")

    ledger.request_erasure(
        "erase-1",
        TENANT_A,
        SUBJECT,
        requested_at=datetime(2027, 4, 1, tzinfo=UTC),
        reason="Retention period expired.",
    )
    exported = ledger.export_subject(TENANT_A, SUBJECT)
    assert exported.key_state == "destroyed"
    assert exported.forecasts == ()
    assert len(exported.tombstones) == 1
    with pytest.raises(SubjectErasedError):
        ledger.issue_forecast(TENANT_A, SUBJECT, claim(), issued_at=NOW, rendered_content="Blocked")


def test_retention_interface_tombstones_only_after_expiry(tmp_path):
    ledger = prepared_ledger(tmp_path)
    assert not ledger.apply_retention_policy(
        "retention-1",
        TENANT_A,
        SUBJECT,
        retain_until=datetime(2028, 1, 1, tzinfo=UTC),
        evaluated_at=datetime(2027, 12, 1, tzinfo=UTC),
    )
    assert ledger.apply_retention_policy(
        "retention-2",
        TENANT_A,
        SUBJECT,
        retain_until=datetime(2028, 1, 1, tzinfo=UTC),
        evaluated_at=datetime(2028, 1, 2, tzinfo=UTC),
    )
    assert ledger.export_subject(TENANT_A, SUBJECT).key_state == "destroyed"


def test_abstentions_and_misses_are_preserved(tmp_path):
    ledger = SQLiteForecastLedger(tmp_path / "abstention.sqlite", outcome_writes_enabled=True)
    ledger.register_release(release())
    ledger.issue_forecast(
        TENANT_A,
        SUBJECT,
        claim(abstained=True),
        issued_at=NOW,
        rendered_content="The system abstained because evidence was insufficient.",
    )
    replayed = ledger.replay_claim(TENANT_A, SUBJECT, "claim-ledger-1")
    assert replayed.abstention.abstained is True


def test_schema_contains_no_raw_birth_pii_columns(tmp_path):
    ledger = SQLiteForecastLedger(tmp_path / "schema.sqlite")
    forbidden = {"name", "birth_date", "birth_time", "latitude", "longitude", "email", "phone"}
    for table in ("consent_events", "issued_forecasts", "resolution_events", "tombstone_events"):
        columns = {row[1] for row in ledger._db.execute(f"PRAGMA table_info({table})")}  # noqa: SLF001, S608
        assert columns.isdisjoint(forbidden)
