"""Open, append-versioned registries for research event and timing semantics."""

from __future__ import annotations

from pydantic import Field, JsonValue, computed_field, model_validator

from .contracts import ResearchModel
from .identity import stable_hash


class EventRegistryEntry(ResearchModel):
    code: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str | None = None
    sensitive: bool = False
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class TimingRegistryEntry(ResearchModel):
    code: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    native_unit: bool = False
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class EventRegistry(ResearchModel):
    registry_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    entries: tuple[EventRegistryEntry, ...]

    @model_validator(mode="after")
    def validate_codes(self) -> EventRegistry:
        _require_unique_codes(entry.code for entry in self.entries)
        return self

    @computed_field
    @property
    def registry_hash(self) -> str:
        return _registry_hash(self)


class TimingRegistry(ResearchModel):
    registry_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    entries: tuple[TimingRegistryEntry, ...]

    @model_validator(mode="after")
    def validate_codes(self) -> TimingRegistry:
        _require_unique_codes(entry.code for entry in self.entries)
        return self

    @computed_field
    @property
    def registry_hash(self) -> str:
        return _registry_hash(self)


def _require_unique_codes(codes: object) -> None:
    values = list(codes)
    if len(values) != len(set(values)):
        raise ValueError("registry entry codes must be unique")


def _registry_hash(registry: EventRegistry | TimingRegistry) -> str:
    return stable_hash(
        {
            "registry_id": registry.registry_id,
            "version": registry.version,
            "description": registry.description,
            "metadata": registry.metadata,
            "entries": [entry.model_dump(mode="json") for entry in registry.entries],
        }
    )


_TIMING_DESCRIPTIONS = {
    "instant": "A single timestamp or technique-native instant.",
    "minute": "A civil-minute resolution.",
    "ghati": "A technique-native ghati resolution.",
    "hora": "A planetary or technique-native hora resolution.",
    "day": "A civil-day resolution.",
    "tithi": "A lunar-day resolution.",
    "week": "A seven-day or source-declared week resolution.",
    "fortnight": "A fortnight or paksha-scale resolution.",
    "month": "A civil, solar, lunar, or source-native month resolution.",
    "quarter": "A three-month or source-declared quarter resolution.",
    "year": "A civil, solar, dasha, or source-native year resolution.",
    "multiyear": "A bounded interval spanning multiple years.",
    "open": "An interval with at least one unbounded endpoint.",
    "native": "An uninterpreted timing representation native to the technique.",
}

DEFAULT_TIMING_REGISTRY = TimingRegistry(
    registry_id="vedicastro-research-timing",
    version="1.0.0",
    entries=tuple(
        TimingRegistryEntry(
            code=code,
            label=code.replace("_", " ").title(),
            description=description,
            native_unit=code in {"ghati", "hora", "tithi", "native"},
        )
        for code, description in _TIMING_DESCRIPTIONS.items()
    ),
)


_RESEARCH_EVENT_ENTRIES = (
    ("health.disease", "health", "Disease indication", True),
    ("health.mortality", "health", "Mortality indication", True),
    ("reproduction.conception", "conception", "Conception indication", True),
    ("reproduction.pregnancy", "pregnancy", "Pregnancy indication", True),
    ("reproduction.childbirth", "childbirth", "Childbirth indication", True),
    ("safety.injury", "injury", "Injury indication", True),
    ("safety.accident", "accident", "Accident indication", True),
    ("safety.violence", "violence", "Violence indication", True),
    ("crime.involvement", "crime", "Crime-related indication", True),
    ("legal.proceeding", "legal", "Legal proceeding", True),
    ("relationship.change", "relationships", "Relationship change", False),
    ("finance.change", "finance", "Finance change", False),
    ("employment.change", "employment", "Employment change", False),
    ("education.milestone", "education", "Education milestone", False),
    ("property.change", "property", "Property change", False),
    ("travel.journey", "travel", "Travel or journey", False),
    ("family.change", "family", "Family change", False),
    ("spiritual.practice", "spiritual", "Spiritual practice", False),
)

DEFAULT_EVENT_REGISTRY = EventRegistry(
    registry_id="vedicastro-research-events",
    version="1.0.0",
    description=(
        "Representative labels for lossless research classification. This open registry is "
        "not a product allowlist and does not authorize publication of any event."
    ),
    metadata={
        "purpose": "research_classification",
        "open_registry": True,
        "is_allowlist": False,
        "authorizes_product_output": False,
    },
    entries=tuple(
        EventRegistryEntry(
            code=code,
            domain=domain,
            label=label,
            sensitive=sensitive,
            metadata={"research_only": True},
        )
        for code, domain, label, sensitive in _RESEARCH_EVENT_ENTRIES
    ),
)
