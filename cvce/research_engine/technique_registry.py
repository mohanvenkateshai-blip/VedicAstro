"""Open technique and school/configuration registry for research experiments."""

from __future__ import annotations

import threading
from collections.abc import Iterable

from pydantic import Field, JsonValue, model_validator

from .contracts import ResearchModel
from .identity import stable_hash
from .immutable import freeze_json, snapshot_model


class TechniqueDefinition(ResearchModel):
    technique_code: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    family: str = Field(min_length=1)
    implementation_ref: str = Field(min_length=1)
    version: str = Field(min_length=1)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def freeze_payloads(self) -> TechniqueDefinition:
        object.__setattr__(self, "metadata", freeze_json(self.metadata))
        return self


class SchoolConfigurationProfile(ResearchModel):
    profile_id: str = Field(min_length=1)
    technique_code: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    school_or_lineage: str | None = None
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    source_references: tuple[str, ...] = ()
    original_payload: JsonValue = Field(default_factory=dict)

    @model_validator(mode="after")
    def freeze_payloads(self) -> SchoolConfigurationProfile:
        object.__setattr__(self, "parameters", freeze_json(self.parameters))
        object.__setattr__(self, "original_payload", freeze_json(self.original_payload))
        return self

    @property
    def profile_hash(self) -> str:
        return stable_hash(self)


class TechniqueRegistry:
    """Thread-safe open registry; arbitrary technique codes are permitted."""

    def __init__(
        self,
        definitions: Iterable[TechniqueDefinition] = (),
        profiles: Iterable[SchoolConfigurationProfile] = (),
    ) -> None:
        self._lock = threading.RLock()
        self._definitions: dict[str, TechniqueDefinition] = {}
        self._profiles: dict[str, SchoolConfigurationProfile] = {}
        for definition in definitions:
            self.register(definition)
        for profile in profiles:
            self.register_profile(profile)

    def register(self, definition: TechniqueDefinition) -> None:
        definition = snapshot_model(definition)
        with self._lock:
            existing = self._definitions.get(definition.technique_code)
            if existing is not None and existing != definition:
                raise ValueError(
                    f"technique code already has a different definition: {definition.technique_code}"
                )
            self._definitions[definition.technique_code] = definition

    def register_profile(self, profile: SchoolConfigurationProfile) -> None:
        profile = snapshot_model(profile)
        with self._lock:
            if profile.technique_code not in self._definitions:
                raise ValueError(
                    f"profile references unregistered technique: {profile.technique_code}"
                )
            existing = self._profiles.get(profile.profile_id)
            if existing is not None and existing != profile:
                raise ValueError(
                    f"profile ID already has a different definition: {profile.profile_id}"
                )
            self._profiles[profile.profile_id] = profile

    def require(self, technique_code: str) -> TechniqueDefinition:
        with self._lock:
            try:
                return self._definitions[technique_code].model_copy(deep=True)
            except KeyError as exc:
                raise KeyError(f"unknown research technique: {technique_code}") from exc

    def definitions(self) -> tuple[TechniqueDefinition, ...]:
        with self._lock:
            return tuple(
                self._definitions[code].model_copy(deep=True) for code in sorted(self._definitions)
            )

    def technique_codes(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._definitions))

    def profiles(self, technique_code: str | None = None) -> tuple[SchoolConfigurationProfile, ...]:
        with self._lock:
            values = self._profiles.values()
            if technique_code is not None:
                values = (item for item in values if item.technique_code == technique_code)
            return tuple(
                item.model_copy(deep=True) for item in sorted(values, key=lambda x: x.profile_id)
            )

    @property
    def registry_hash(self) -> str:
        return stable_hash(
            {
                "techniques": [item.model_dump(mode="json") for item in self.definitions()],
                "profiles": [item.model_dump(mode="json") for item in self.profiles()],
            }
        )


def _known(code: str, name: str, family: str, implementation: str) -> TechniqueDefinition:
    return TechniqueDefinition(
        technique_code=code,
        display_name=name,
        family=family,
        implementation_ref=implementation,
        version="open-registry.1",
    )


DEFAULT_TECHNIQUE_REGISTRY = TechniqueRegistry(
    (
        _known("natal", "Natal", "chart", "vedic_engine.core"),
        _known("panchanga", "Panchanga", "calendar", "vedic_engine.core.panchanga"),
        _known("vimshottari", "Vimshottari", "dasha", "vedic_engine.prediction.dasha"),
        _known("yogini", "Yogini", "dasha", "app.yogini_predict"),
        _known("chara", "Chara", "dasha", "vedic_engine.prediction.chara_dasha"),
        _known("kalachakra", "Kalachakra", "dasha", "app.kalachakra"),
        _known("kp", "KP", "stellar", "vedic_engine.prediction.kp_system"),
        _known("prashna", "Prashna", "horary", "vedic_engine.prediction.prashna"),
        _known("gochar", "Gochar", "transit", "vedic_engine.prediction.gochar"),
        _known(
            "ashtakavarga",
            "Ashtakavarga",
            "strength",
            "vedic_engine.prediction.ashtakavarga",
        ),
        _known("yoga", "Yoga", "combination", "vedic_engine.prediction.yoga"),
        _known("muhurta", "Muhurta", "electional", "vedic_engine.prediction.muhurta_yogas"),
    )
)
