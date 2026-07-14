from __future__ import annotations

import json
from pathlib import Path

from forecasting.generate_artifacts import REPOSITORY_ROOT, render_artifacts, write_artifacts


def test_checked_in_contract_artifacts_match_python_sources():
    assert write_artifacts(check=True) == []
    for relative_path, expected in render_artifacts().items():
        assert (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8") == expected


def test_traditional_strength_schema_is_never_labelled_as_probability():
    schema_path = REPOSITORY_ROOT / "docs/forecast_contract.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    strength = schema["properties"]["traditional_strength_index"]
    human_labels = " ".join(
        str(strength.get(key, "")) for key in ("title", "description", "$comment")
    ).lower()

    assert "probability" not in human_labels
    assert "forecast_probability" in schema["properties"]
    assert schema["properties"]["forecast_probability"] != strength


def test_artifact_paths_are_repository_relative_and_versioned():
    artifacts = render_artifacts()
    assert all(not path.is_absolute() for path in artifacts)
    assert all(isinstance(path, Path) for path in artifacts)

    for path, content in artifacts.items():
        if path.suffix == ".json":
            assert json.loads(content)["x-artifact-version"] == "1.0.0"
        else:
            assert 'artifact_version: "1.0.0"' in content
