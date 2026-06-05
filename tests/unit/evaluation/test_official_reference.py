from __future__ import annotations

from pathlib import Path

from fdm_1_with_d2e.evaluation import (
    DEFAULT_DATASET_ID,
    DEFAULT_MODEL_ID,
    DEFAULT_UPSTREAM_COMMIT,
    D2EDeviation,
    build_evaluate_command,
    build_inference_command,
    build_official_reference_record,
    default_offline_deviations,
    load_official_reference_record,
    reference_summary,
    shell_join,
    stable_json_dumps,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_official_reference_record_is_pinned_and_offline() -> None:
    record = build_official_reference_record()

    assert record["upstream_commit"] == DEFAULT_UPSTREAM_COMMIT
    assert record["model_id"] == DEFAULT_MODEL_ID
    assert record["dataset_id"] == DEFAULT_DATASET_ID
    assert record["default_tests_offline"] is True
    assert record["network_required_for_live_check"] is True
    assert record["command_templates"]["inference"].startswith("uv run inference.py")
    assert record["command_templates"]["evaluate"].startswith("uv run evaluate.py")
    assert record["official_metric_timebase_ms"] == 50
    assert record["deviation_table"]


def test_command_builders_use_uv_run() -> None:
    inference = build_inference_command("gameplay.mp4", "predicted.mcap", max_duration_seconds=30)
    evaluate = build_evaluate_command("gt.mcap", "pred.mcap", "results.json")

    assert inference[:3] == ("uv", "run", "inference.py")
    assert evaluate[:3] == ("uv", "run", "evaluate.py")
    assert shell_join(evaluate) == "uv run evaluate.py gt.mcap pred.mcap --output results.json"


def test_deviation_table_entries_are_json_records() -> None:
    table = [entry.to_json() for entry in default_offline_deviations()]

    assert {entry["deviation_id"] for entry in table} >= {
        "official_evaluate_py_not_invoked_in_default_tests",
        "local_scale_ratio_formula_reimplementation",
        "writer_records_are_not_mcap_files",
    }
    assert all(entry["followup"] for entry in table)


def test_committed_reference_record_loads_without_network() -> None:
    record = load_official_reference_record(REPO_ROOT / "configs/data/d2e_reference.json")
    summary = reference_summary(record)

    assert summary["status"] == "official_reference_record_available"
    assert summary["offline_only"] is True
    assert summary["upstream_commit"] == DEFAULT_UPSTREAM_COMMIT
    assert summary["deviation_count"] >= 3


def test_committed_reference_record_matches_default_builder() -> None:
    expected = stable_json_dumps(build_official_reference_record()) + "\n"

    assert (REPO_ROOT / "configs/data/d2e_reference.json").read_text(encoding="utf-8") == expected


def test_custom_deviation_can_be_embedded() -> None:
    deviation = D2EDeviation(
        deviation_id="fixture_only",
        category="test",
        status="known",
        official_behavior="official",
        local_behavior="local",
        reason="offline",
        followup="run official smoke",
    )

    record = build_official_reference_record(deviations=(deviation,))

    assert record["deviation_table"] == [deviation.to_json()]
