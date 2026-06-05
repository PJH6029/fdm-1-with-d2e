from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_STORY_ID = "G001-bootstrap-package-configs-and-schema"
IMPLEMENTED_MANIFEST_STORY_ID = "G004-implement-manifests-and-action-distr"
EVALUATOR_STORY_ID = "G005-implement-evaluator-and-official-d2e"
ALLOWED_STORY_IDS = {BOOTSTRAP_STORY_ID, IMPLEMENTED_MANIFEST_STORY_ID, EVALUATOR_STORY_ID}

CONFIG_PATHS = [
    Path("configs/data/bootstrap_dataset_manifest.json"),
    Path("configs/data/bootstrap_splits.json"),
    Path("configs/data/bootstrap_scales.json"),
    Path("configs/data/bootstrap_action_distribution.json"),
    Path("configs/data/phase0_manifest_builders.json"),
    Path("configs/data/d2e_reference.json"),
    Path("configs/tokenization/default.json"),
    Path("configs/evaluation/d2e_local.json"),
    Path("configs/experiments/phase-0-data/bootstrap_offline.json"),
]


def _load_json(path: Path) -> dict:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def _matches_json_type(value: object, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    raise AssertionError(f"unsupported schema type in bootstrap validator: {expected}")


def _validate_minimal_schema(schema: dict, instance: object, where: str) -> None:
    expected_type = schema.get("type")
    if isinstance(expected_type, list):
        assert any(_matches_json_type(instance, item) for item in expected_type), where
    elif isinstance(expected_type, str):
        assert _matches_json_type(instance, expected_type), where

    if "const" in schema:
        assert instance == schema["const"], where
    if "enum" in schema:
        assert instance in schema["enum"], where

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            assert key in instance, f"{where}.{key} missing"
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(instance) - set(properties))
            assert not extra, f"{where} has extra keys {extra}"
        for key, value in instance.items():
            child_schema = properties.get(key)
            if child_schema is not None:
                _validate_minimal_schema(child_schema, value, f"{where}.{key}")
    elif isinstance(instance, list):
        if "minItems" in schema:
            assert len(instance) >= schema["minItems"], where
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, value in enumerate(instance):
                _validate_minimal_schema(item_schema, value, f"{where}[{index}]")


def test_schemas_are_valid_json_schema_documents() -> None:
    schema_paths = sorted((REPO_ROOT / "schemas").glob("*.schema.json"))
    assert schema_paths, "G001 should commit JSON schema files"
    for path in schema_paths:
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["$schema"].startswith("https://json-schema.org/")
        assert schema["type"] == "object"
        assert schema["title"]
        assert schema["required"]


def test_committed_configs_validate_against_local_schema_subset() -> None:
    for config_path in CONFIG_PATHS:
        config = _load_json(config_path)
        assert config.get("created_by_story") in ALLOWED_STORY_IDS or config.get("story_id") in ALLOWED_STORY_IDS
        schema_path = Path(config["schema"])
        assert schema_path.parts[0] == "schemas"
        schema = _load_json(schema_path)
        _validate_minimal_schema(schema, config, str(config_path))


def test_bootstrap_configs_preserve_phase0_canonical_defaults() -> None:
    tokenization = _load_json(Path("configs/tokenization/default.json"))
    evaluation = _load_json(Path("configs/evaluation/d2e_local.json"))
    experiment = _load_json(Path("configs/experiments/phase-0-data/bootstrap_offline.json"))

    assert tokenization["timebase_ms"] == 50
    assert tokenization["sparse_event_slots"] == 8
    assert tokenization["mouse_bins_per_axis"] == 49
    assert {
        "MASK_ACTION",
        "NO_ACTION",
        "PAD_ACTION",
        "BOS_ACTION",
        "EOS_ACTION",
        "EVENT_OVERFLOW",
    }.issubset(tokenization["special_tokens"])

    assert evaluation["timebase_ms"] == 50
    assert evaluation["official_reference"] == "configs/data/d2e_reference.json"
    assert experiment["offline_only"] is True
    assert {"live_network", "hugging_face_download", "mlxp", "d2e_dataset"}.issubset(
        experiment["prohibited_inputs"]
    )
