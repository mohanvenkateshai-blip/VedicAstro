"""Generate reviewable contract artifacts from the forecasting source of truth.

This module deliberately uses only the Python standard library and Pydantic.
The YAML renderer supports the small JSON-compatible subset used by the event
ontology, so artifact generation does not add a PyYAML runtime dependency.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .contracts import CURRENT_CONTRACT_VERSION, ForecastClaim
from .ledger import ModelRelease, OutcomeObservation
from .taxonomy import EVENT_TAXONOMY

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_VERSION = CURRENT_CONTRACT_VERSION


def _json_schema(model: type[ForecastClaim | OutcomeObservation | ModelRelease]) -> str:
    schema = model.model_json_schema(mode="validation")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"https://vedicastro.local/schemas/{model.__name__}/{ARTIFACT_VERSION}"
    schema["x-artifact-version"] = ARTIFACT_VERSION
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _ontology_document() -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for code, definition in EVENT_TAXONOMY.items():
        events.append(
            {
                "code": code.value,
                "domain": definition.domain.value,
                "leaf": code.leaf,
                "observable_predicate": definition.observable_predicate,
                "target_entity": definition.target_entity,
                "inclusion_criteria": list(definition.inclusion_criteria),
                "exclusion_criteria": list(definition.exclusion_criteria),
                "evidence_hierarchy": list(definition.evidence_hierarchy),
                "resolution_policy": definition.resolution_policy,
                "default_horizon_days": definition.default_horizon_days,
                "maximum_horizon_days": definition.maximum_horizon_days,
                "permitted_granularities": list(definition.permitted_granularities),
                "censoring_policy": definition.censoring_policy,
                "sensitivity": definition.sensitivity.value,
                "requires_explicit_opt_in": definition.requires_explicit_opt_in,
            }
        )
    return {
        "artifact_version": ARTIFACT_VERSION,
        "source": "cvce.forecasting.taxonomy.EVENT_TAXONOMY",
        "closed_ontology": True,
        "event_count": len(events),
        "events": events,
    }


def _yaml_scalar(value: object) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int | float):
        return str(value)
    raise TypeError(f"unsupported YAML scalar: {type(value).__name__}")


def _yaml_lines(value: object, indent: int = 0) -> list[str]:
    prefix = " " * indent
    if isinstance(value, Mapping):
        if not value:
            return [prefix + "{}"]
        lines: list[str] = []
        for key, child in value.items():
            if isinstance(child, Mapping | list) and child:
                lines.append(f"{prefix}{key}:")
                lines.extend(_yaml_lines(child, indent + 2))
            elif isinstance(child, Mapping | list):
                lines.append(f"{prefix}{key}: {'{}' if isinstance(child, Mapping) else '[]'}")
            else:
                lines.append(f"{prefix}{key}: {_yaml_scalar(child)}")
        return lines
    if isinstance(value, list):
        if not value:
            return [prefix + "[]"]
        lines = []
        for child in value:
            if isinstance(child, Mapping):
                items = list(child.items())
                if not items:
                    lines.append(prefix + "- {}")
                    continue
                first_key, first_value = items[0]
                if isinstance(first_value, Mapping | list) and first_value:
                    lines.append(f"{prefix}- {first_key}:")
                    lines.extend(_yaml_lines(first_value, indent + 4))
                elif isinstance(first_value, Mapping | list):
                    empty = "{}" if isinstance(first_value, Mapping) else "[]"
                    lines.append(f"{prefix}- {first_key}: {empty}")
                else:
                    lines.append(f"{prefix}- {first_key}: {_yaml_scalar(first_value)}")
                for key, item in items[1:]:
                    if isinstance(item, Mapping | list) and item:
                        lines.append(f"{prefix}  {key}:")
                        lines.extend(_yaml_lines(item, indent + 4))
                    elif isinstance(item, Mapping | list):
                        empty = "{}" if isinstance(item, Mapping) else "[]"
                        lines.append(f"{prefix}  {key}: {empty}")
                    else:
                        lines.append(f"{prefix}  {key}: {_yaml_scalar(item)}")
            elif isinstance(child, list):
                lines.append(prefix + "-")
                lines.extend(_yaml_lines(child, indent + 2))
            else:
                lines.append(f"{prefix}- {_yaml_scalar(child)}")
        return lines
    return [prefix + _yaml_scalar(value)]


def _event_ontology_yaml() -> str:
    header = (
        "# Generated from cvce/forecasting/taxonomy.py.\n"
        "# Run: cd cvce && .venv/bin/python -m forecasting.generate_artifacts\n"
    )
    return header + "\n".join(_yaml_lines(_ontology_document())) + "\n"


ARTIFACT_BUILDERS: Mapping[Path, Callable[[], str]] = {
    Path("docs/forecast_contract.schema.json"): lambda: _json_schema(ForecastClaim),
    Path("docs/outcome_observation.schema.json"): lambda: _json_schema(OutcomeObservation),
    Path("docs/model_release.schema.json"): lambda: _json_schema(ModelRelease),
    Path("docs/forecast_event_ontology.yaml"): _event_ontology_yaml,
}


def render_artifacts() -> dict[Path, str]:
    """Return every relative artifact path and its canonical content."""

    return {path: builder() for path, builder in ARTIFACT_BUILDERS.items()}


def write_artifacts(root: Path = REPOSITORY_ROOT, *, check: bool = False) -> list[Path]:
    """Write artifacts, or return drifted paths without writing in check mode."""

    drifted: list[Path] = []
    for relative_path, content in render_artifacts().items():
        path = root / relative_path
        existing = path.read_text(encoding="utf-8") if path.exists() else None
        if existing == content:
            continue
        drifted.append(relative_path)
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    return drifted


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if checked-in artifacts differ from their Python sources",
    )
    args = parser.parse_args(argv)
    drifted = write_artifacts(check=args.check)
    if args.check and drifted:
        print("Contract artifacts are stale:")
        for path in drifted:
            print(f"- {path}")
        print("Run: cd cvce && .venv/bin/python -m forecasting.generate_artifacts")
        return 1
    for path in drifted:
        print(f"generated {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
