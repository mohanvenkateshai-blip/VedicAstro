"""Deterministic, claim-grounded prediction verbalisation for ``en-IN``.

This module deliberately does not call an LLM.  It verbalises exactly one
validated :class:`ForecastClaim`, preserves uncertainty, and refuses broad
multi-domain bucket text instead of turning it into an actionable forecast.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date

from forecasting.contracts import (
    BirthTimeSensitivity,
    ForecastClaim,
    ForecastPolarity,
    ProbabilityStatus,
)
from prediction_policy import filter_personalised_claim_text

from .models import ContentPlan, EvidenceSummary, GroundedText, PredictionBrief

_DOMAIN_TERMS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:job|career|employ(?:ment|er)|promotion)\b",
        r"\b(?:contract|agreement|signature)\b",
        r"\b(?:travel|journey|trip|flight)\b",
        r"\b(?:residence|house|home|relocat(?:e|ion)|move)\b",
        r"\b(?:education|study|course|credential|enrolment)\b",
        r"\b(?:marriage|wedding|relationship|ceremon(?:y|ies))\b",
    )
)
_DISPLAY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


class VerbalizationError(ValueError):
    """Base error for a claim that cannot be verbalised faithfully."""


class UnsupportedLocaleError(VerbalizationError):
    """Raised when no deterministic locale renderer is available."""


class BroadBucketError(VerbalizationError):
    """Raised for vague text that combines unrelated prediction domains."""


class GroundingError(VerbalizationError):
    """Raised when a plan contains an assertion not derivable from its claim."""


def build_content_plan(claim: ForecastClaim) -> ContentPlan:
    """Build and validate a deterministic plan for one validated claim."""

    plan = _build_content_plan(claim)
    validate_grounding(plan, claim)
    return plan


def validate_grounding(plan: ContentPlan, claim: ForecastClaim) -> None:
    """Reject any plan that differs from the canonical plan for ``claim``.

    Exact structural equality is intentional: it proves every visible
    assertion and source path was produced from the supplied immutable claim,
    rather than merely checking whether selected keywords happen to occur.
    """

    expected = _build_content_plan(claim)
    if plan != expected:
        raise GroundingError("content plan contains assertions not grounded in the claim")


def render_prediction_brief(claim: ForecastClaim) -> PredictionBrief:
    """Return concise and paragraph forms without adding facts to the plan."""

    plan = build_content_plan(claim)
    if plan.abstention:
        concise = f"{plan.abstention.text} Window assessed: {plan.timing.text}"
        paragraphs = (
            concise,
            f"Event assessed: {plan.event.text} {plan.birth_time_stability.text}",
            _join_sections(plan.probability.text, *(item.text for item in plan.limitations)),
        )
    else:
        concise = f"{plan.implication.text} Expected event: {plan.event.text} {plan.timing.text}"
        expectation = _labelled("What to expect", plan.expectations)
        prerequisites = _labelled("Prerequisites", plan.prerequisites)
        evidence = " ".join(item.statement.text for item in plan.evidence)
        action = _labelled("Safe next steps", plan.safe_actions)
        caveats = _join_sections(
            plan.probability.text,
            plan.birth_time_stability.text,
            *(item.text for item in plan.limitations),
        )
        paragraphs = tuple(
            part
            for part in (
                concise,
                _join_sections(expectation, prerequisites),
                evidence,
                action,
                caveats,
            )
            if part
        )
    return PredictionBrief(
        claim_id=claim.claim_id,
        concise_sentence=concise,
        paragraphs=paragraphs,
        content_plan=plan,
    )


def _build_content_plan(claim: ForecastClaim) -> ContentPlan:
    if claim.locale != "en-IN":
        raise UnsupportedLocaleError(f"unsupported verbalisation locale: {claim.locale}")

    free_text = (
        *claim.what_to_expect,
        *claim.prerequisites,
        *claim.safe_next_steps,
        *claim.avoidance_advice,
        *claim.limitations,
        claim.decision_scope,
    )
    for text in free_text:
        _reject_broad_bucket(text)

    policy_blocked_paths = _policy_blocked_paths(claim)
    policy_blocked = bool(policy_blocked_paths)
    abstention = _abstention(claim, policy_blocked_paths)
    return ContentPlan(
        claim_id=claim.claim_id,
        event=_ground(claim.observable_outcome, "observable_outcome"),
        timing=_ground(_timing_text(claim), "timing"),
        implication=_ground(_implication_text(claim, bool(abstention)), "polarity"),
        expectations=()
        if policy_blocked
        else _ground_many(claim.what_to_expect, "what_to_expect"),
        prerequisites=()
        if policy_blocked
        else _ground_many(claim.prerequisites, "prerequisites"),
        evidence=_evidence(claim),
        safe_actions=()
        if policy_blocked
        else (
            *_ground_many(claim.safe_next_steps, "safe_next_steps"),
            *_ground_many(claim.avoidance_advice, "avoidance_advice"),
        ),
        limitations=()
        if policy_blocked
        else (
            *_ground_many(claim.limitations, "limitations"),
            _ground(claim.decision_scope, "decision_scope"),
        ),
        probability=_ground(
            _probability_text(claim),
            "probability_status",
            *("forecast_probability", "calibration_release_id")
            if claim.probability_status is ProbabilityStatus.CALIBRATED
            else (),
        ),
        birth_time_stability=_ground(
            _birth_stability_text(claim), "uncertainty.birth_time_sensitivity"
        ),
        abstention=abstention,
    )


def _ground(text: str, *paths: str) -> GroundedText:
    return GroundedText(text=text.strip(), source_paths=tuple(paths))


def _ground_many(values: Iterable[str], path: str) -> tuple[GroundedText, ...]:
    return tuple(_ground(value, f"{path}.{index}") for index, value in enumerate(values))


def _timing_text(claim: ForecastClaim) -> str:
    timing = claim.timing
    start = _display_date(timing.start_on, include_year=timing.start_on.year != timing.end_on.year)
    end = _display_date(timing.end_on, include_year=True)
    return (
        f"Window: {start} to {end} "
        f"({timing.granularity.value}-level, {timing.timezone})."
    )


def _display_date(value: date, *, include_year: bool) -> str:
    text = f"{value.day} {value.strftime('%B')}"
    return f"{text} {value.year}" if include_year else text


def _implication_text(claim: ForecastClaim, abstained: bool) -> str:
    if abstained:
        return "No directional forecast is issued."
    return {
        ForecastPolarity.FAVOURABLE: "Favourable: the available signal supports this outcome.",
        ForecastPolarity.UNFAVOURABLE: "Unfavourable: the available signal weighs against this outcome.",
        ForecastPolarity.MIXED: "Mixed: supporting and opposing signals are both present.",
        ForecastPolarity.INDETERMINATE: "Indeterminate: the available signal has no stable direction.",
    }[claim.polarity]


def _probability_text(claim: ForecastClaim) -> str:
    if claim.probability_status is ProbabilityStatus.CALIBRATED:
        _require_display_id(claim.calibration_release_id or "", "calibration_release_id")
        probability = round((claim.forecast_probability or 0) * 100)
        return (
            f"Calibrated forecast probability: {probability}% "
            f"(release {claim.calibration_release_id})."
        )
    if claim.probability_status is ProbabilityStatus.UNCALIBRATED_SIGNAL:
        return "This is a traditional, uncalibrated signal; it is not an empirical probability."
    return "No empirical probability is available for this claim."


def _birth_stability_text(claim: ForecastClaim) -> str:
    return {
        BirthTimeSensitivity.STABLE: "Birth-time stability: stable across the tested times.",
        BirthTimeSensitivity.MODERATE: "Birth-time stability: moderately sensitive to the recorded time.",
        BirthTimeSensitivity.HIGH: "Birth-time stability: highly sensitive to the recorded time.",
        BirthTimeSensitivity.UNKNOWN: "Birth-time stability: not assessed.",
    }[claim.uncertainty.birth_time_sensitivity]


def _evidence(claim: ForecastClaim) -> tuple[EvidenceSummary, ...]:
    summaries: list[EvidenceSummary] = []
    for direction, ids, path in (
        ("supporting", claim.supporting_evidence_ids, "supporting_evidence_ids"),
        ("opposing", claim.opposing_evidence_ids, "opposing_evidence_ids"),
    ):
        for evidence_id in ids:
            _require_display_id(evidence_id, path)
        count = len(ids)
        identifier_text = ", ".join(ids) if ids else "none"
        statement = f"{direction.title()} evidence ({count}): {identifier_text}."
        summaries.append(
            EvidenceSummary(
                direction=direction,
                evidence_ids=ids,
                statement=_ground(statement, path),
            )
        )
    return tuple(summaries)


def _abstention(
    claim: ForecastClaim, policy_blocked_paths: tuple[str, ...]
) -> GroundedText | None:
    if policy_blocked_paths:
        return _ground(
            "No personalised prediction is provided because the claim contains a blocked high-severity topic.",
            *policy_blocked_paths,
        )
    if not claim.abstention.abstained:
        return None
    return _ground(
        f"No prediction is issued: {claim.abstention.reason}",
        "abstention.abstained",
        "abstention.code",
        "abstention.reason",
    )


def _policy_blocked_paths(claim: ForecastClaim) -> tuple[str, ...]:
    values = (
        ("observable_outcome", claim.observable_outcome),
        *((f"what_to_expect.{index}", value) for index, value in enumerate(claim.what_to_expect)),
        *((f"prerequisites.{index}", value) for index, value in enumerate(claim.prerequisites)),
        *((f"safe_next_steps.{index}", value) for index, value in enumerate(claim.safe_next_steps)),
        *((f"avoidance_advice.{index}", value) for index, value in enumerate(claim.avoidance_advice)),
        *((f"limitations.{index}", value) for index, value in enumerate(claim.limitations)),
        ("decision_scope", claim.decision_scope),
        ("abstention.reason", claim.abstention.reason or ""),
    )
    return tuple(
        path
        for path, text in values
        if filter_personalised_claim_text(text).blocked_count
    )


def _reject_broad_bucket(text: str) -> None:
    represented_domains = sum(bool(pattern.search(text)) for pattern in _DOMAIN_TERMS)
    if represented_domains > 1:
        raise BroadBucketError(
            "prediction prose combines multiple event domains; issue one observable claim at a time"
        )


def _require_display_id(value: str, path: str) -> None:
    if not _DISPLAY_ID.fullmatch(value):
        raise VerbalizationError(f"{path} contains an unsafe display identifier")


def _labelled(label: str, values: tuple[GroundedText, ...]) -> str:
    if not values:
        return ""
    return f"{label}: {' '.join(value.text for value in values)}"


def _join_sections(*parts: str) -> str:
    return " ".join(part for part in parts if part)
