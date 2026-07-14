"""Policy-neutral capture and replay foundation for prediction research."""

from .contracts import (
    RawPrediction,
    RawScore,
    RawTiming,
    ResearchAnnotation,
    RunArtifactReference,
    RunStatus,
    TechniqueConfiguration,
    TechniqueItemError,
    TechniqueRun,
    TechniqueRunError,
    TimingTolerance,
)
from .identity import canonical_json, stable_hash
from .registries import (
    DEFAULT_EVENT_REGISTRY,
    DEFAULT_TIMING_REGISTRY,
    EventRegistry,
    EventRegistryEntry,
    TimingRegistry,
    TimingRegistryEntry,
)
from .store import (
    ImmutableResearchStore,
    ResearchStoreConflict,
    ResearchStoreError,
    ResearchStoreIntegrityError,
    ResearchStoreSchemaError,
)

__all__ = [
    "DEFAULT_EVENT_REGISTRY",
    "DEFAULT_TIMING_REGISTRY",
    "EventRegistry",
    "EventRegistryEntry",
    "ImmutableResearchStore",
    "RawPrediction",
    "RawScore",
    "RawTiming",
    "ResearchAnnotation",
    "ResearchStoreConflict",
    "ResearchStoreError",
    "ResearchStoreIntegrityError",
    "ResearchStoreSchemaError",
    "RunArtifactReference",
    "RunStatus",
    "TechniqueConfiguration",
    "TechniqueItemError",
    "TechniqueRun",
    "TechniqueRunError",
    "TimingRegistry",
    "TimingRegistryEntry",
    "TimingTolerance",
    "canonical_json",
    "stable_hash",
]
