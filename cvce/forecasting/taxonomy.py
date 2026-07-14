"""Closed v1 ontology for low-risk, objectively resolvable forecast events."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EventDomain(StrEnum):
    EMPLOYMENT = "employment"
    CONTRACT = "contract"
    TRAVEL = "travel"
    RESIDENCE = "residence"
    EDUCATION = "education"
    RELATIONSHIP = "relationship"


class EventCode(StrEnum):
    """Leaf nodes in the event hierarchy.

    The dot-separated value is the stable machine identity.  Its first segment
    is the parent domain; downstream code must not infer a second event from a
    broad prose label such as ``career`` or ``relationships``.
    """

    EMPLOYMENT_OFFER_RECEIVED = "employment.offer_received"
    EMPLOYMENT_START = "employment.start"
    EMPLOYMENT_INVOLUNTARY_END = "employment.involuntary_end"
    CONTRACT_SIGNED = "contract.signed"
    TRAVEL_DEPARTURE_INTERNATIONAL = "travel.departure_international"
    RESIDENCE_MOVE_COMPLETED = "residence.move_completed"
    EDUCATION_ENROLMENT = "education.enrolment"
    EDUCATION_CREDENTIAL_COMPLETED = "education.credential_completed"
    RELATIONSHIP_MARRIAGE_REGISTERED = "relationship.marriage_registered"

    @property
    def domain(self) -> EventDomain:
        return EventDomain(self.value.split(".", maxsplit=1)[0])

    @property
    def leaf(self) -> str:
        return self.value.split(".", maxsplit=1)[1]


class EventSensitivity(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    SENSITIVE_OPT_IN = "sensitive_opt_in"


@dataclass(frozen=True, slots=True)
class EventDefinition:
    """Resolution semantics for one ontology leaf."""

    code: EventCode
    observable_predicate: str
    target_entity: str
    inclusion_criteria: tuple[str, ...]
    exclusion_criteria: tuple[str, ...]
    evidence_hierarchy: tuple[str, ...]
    resolution_policy: str
    default_horizon_days: int
    maximum_horizon_days: int
    permitted_granularities: tuple[str, ...]
    censoring_policy: str
    sensitivity: EventSensitivity = EventSensitivity.LOW
    requires_explicit_opt_in: bool = False

    @property
    def domain(self) -> EventDomain:
        return self.code.domain

    @property
    def hierarchy(self) -> tuple[str, str]:
        return (self.domain.value, self.code.value)


def _definition(
    code: EventCode,
    predicate: str,
    *,
    inclusion: tuple[str, ...],
    exclusion: tuple[str, ...] = (),
    evidence: tuple[str, ...] = ("official_record", "dated_document", "subject_attestation"),
    resolution: str,
    default_horizon_days: int = 90,
    maximum_horizon_days: int = 365,
    granularities: tuple[str, ...] = ("day", "week", "month"),
    censoring: str = "indeterminate_if_observation_window_or_evidence_is_incomplete",
    sensitivity: EventSensitivity = EventSensitivity.LOW,
    opt_in: bool = False,
) -> EventDefinition:
    return EventDefinition(
        code=code,
        observable_predicate=predicate,
        target_entity="native",
        inclusion_criteria=inclusion,
        exclusion_criteria=exclusion,
        evidence_hierarchy=evidence,
        resolution_policy=resolution,
        default_horizon_days=default_horizon_days,
        maximum_horizon_days=maximum_horizon_days,
        permitted_granularities=granularities,
        censoring_policy=censoring,
        sensitivity=sensitivity,
        requires_explicit_opt_in=opt_in,
    )


EVENT_TAXONOMY: dict[EventCode, EventDefinition] = {
    EventCode.EMPLOYMENT_OFFER_RECEIVED: _definition(
        EventCode.EMPLOYMENT_OFFER_RECEIVED,
        "The native receives a dated offer for paid employment.",
        inclusion=("A specific role, employer, and proposed start or response date are stated.",),
        exclusion=("Informal interest or an interview without an offer is excluded.",),
        resolution="Resolve positive on receipt of the offer, whether or not it is accepted.",
    ),
    EventCode.EMPLOYMENT_START: _definition(
        EventCode.EMPLOYMENT_START,
        "The native begins paid work in a new employment engagement.",
        inclusion=("At least one paid working day is completed.",),
        exclusion=("An accepted offer that has not started is excluded.",),
        resolution="Resolve positive on the first paid working day.",
    ),
    EventCode.EMPLOYMENT_INVOLUNTARY_END: _definition(
        EventCode.EMPLOYMENT_INVOLUNTARY_END,
        "The native's employment ends at the employer's initiative.",
        inclusion=("Dismissal, redundancy, or employer-initiated non-renewal is documented.",),
        exclusion=("Voluntary resignation and planned retirement are excluded.",),
        resolution="Resolve positive on the effective end date in the employer notice.",
        sensitivity=EventSensitivity.MODERATE,
    ),
    EventCode.CONTRACT_SIGNED: _definition(
        EventCode.CONTRACT_SIGNED,
        "The native becomes a signatory to a dated, binding contract.",
        inclusion=("The agreement identifies the parties, obligations, and signature date.",),
        exclusion=("Drafts, negotiations, and non-binding expressions of interest are excluded.",),
        resolution="Resolve positive when all signatures required for execution are present.",
    ),
    EventCode.TRAVEL_DEPARTURE_INTERNATIONAL: _definition(
        EventCode.TRAVEL_DEPARTURE_INTERNATIONAL,
        "The native departs their country of residence for international travel.",
        inclusion=("A physical border crossing out of the country of residence occurs.",),
        exclusion=("Booking, planning, and domestic travel are excluded.",),
        resolution="Resolve positive at the recorded departure border crossing.",
    ),
    EventCode.RESIDENCE_MOVE_COMPLETED: _definition(
        EventCode.RESIDENCE_MOVE_COMPLETED,
        "The native begins living at a different primary residence.",
        inclusion=("The new address becomes the native's primary overnight residence.",),
        exclusion=("Temporary stays and an unsigned intention to move are excluded.",),
        resolution="Resolve positive on the first day the new address is the primary residence.",
    ),
    EventCode.EDUCATION_ENROLMENT: _definition(
        EventCode.EDUCATION_ENROLMENT,
        "The native formally enrols in a named education programme.",
        inclusion=("The institution confirms active enrolment in a specific programme.",),
        exclusion=("Applications, offers, and informal study are excluded.",),
        resolution="Resolve positive on the institution's effective enrolment date.",
    ),
    EventCode.EDUCATION_CREDENTIAL_COMPLETED: _definition(
        EventCode.EDUCATION_CREDENTIAL_COMPLETED,
        "The native satisfies the requirements for a named education credential.",
        inclusion=("The awarding institution confirms completion or conferral.",),
        exclusion=("Expected completion and partial course completion are excluded.",),
        resolution="Resolve positive on the official completion or conferral date.",
        maximum_horizon_days=730,
    ),
    EventCode.RELATIONSHIP_MARRIAGE_REGISTERED: _definition(
        EventCode.RELATIONSHIP_MARRIAGE_REGISTERED,
        "The native's marriage is registered by a competent authority.",
        inclusion=("A civil or legally recognised marriage registration is recorded.",),
        exclusion=(
            "Dating, engagement, ceremonies without registration, and third-party marriages are excluded.",
        ),
        evidence=("official_record", "dated_document"),
        resolution="Resolve positive on the official registration date.",
        maximum_horizon_days=730,
        sensitivity=EventSensitivity.SENSITIVE_OPT_IN,
        opt_in=True,
    ),
}


def get_event_definition(code: EventCode | str) -> EventDefinition:
    """Return one authoritative definition or raise for an unknown event."""

    return EVENT_TAXONOMY[EventCode(code)]


if set(EVENT_TAXONOMY) != set(EventCode):  # pragma: no cover - import-time invariant
    raise RuntimeError("Every EventCode must have exactly one taxonomy definition")
