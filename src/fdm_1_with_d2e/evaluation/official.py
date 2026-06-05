"""Pinned official D2E reference records and deviation-table helpers.

This module is intentionally offline by default. It records the upstream D2E
revision and command templates that later real-D2E/MLXP stories should execute,
while local tests can verify the record without cloning GitHub or downloading
Hugging Face assets.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import json
from pathlib import Path
import shlex
from typing import Any

from fdm_1_with_d2e.evaluation.d2e_metrics import EVALUATOR_STORY_ID, LOCAL_EVALUATOR_ID, LOCAL_METRIC_REVISION

D2E_REFERENCE_SCHEMA = "schemas/d2e_reference.schema.json"
DEFAULT_UPSTREAM_REPO = "https://github.com/worv-ai/D2E"
DEFAULT_UPSTREAM_COMMIT = "80e98e26e4dc584ec76fec5789b4a97c275dd032"
DEFAULT_UPSTREAM_CHECKED_AT = "2026-06-05"
DEFAULT_MODEL_ID = "open-world-agents/Generalist-IDM-1B"
DEFAULT_DATASET_ID = "open-world-agents/D2E-480p"
DEFAULT_REFERENCE_CONFIG = Path("configs/data/d2e_reference.json")
DEFAULT_EVALUATION_CONFIG = Path("configs/evaluation/d2e_local.json")

JSONDict = dict[str, Any]


@dataclass(frozen=True, slots=True)
class D2EDeviation:
    """One documented local-vs-official evaluator boundary or blocker."""

    deviation_id: str
    category: str
    status: str
    official_behavior: str
    local_behavior: str
    reason: str
    followup: str
    severity: str = "medium"

    def to_json(self) -> JSONDict:
        return {
            "deviation_id": self.deviation_id,
            "category": self.category,
            "status": self.status,
            "severity": self.severity,
            "official_behavior": self.official_behavior,
            "local_behavior": self.local_behavior,
            "reason": self.reason,
            "followup": self.followup,
        }


@dataclass(frozen=True, slots=True)
class D2ECommandTemplates:
    """Reusable official D2E command templates and concrete command builders."""

    inference: str = "uv run inference.py {gameplay_mp4} {predicted_mcap} --max-duration {max_duration_seconds}"
    evaluate: str = "uv run evaluate.py {ground_truth_mcap} {predicted_mcap} --output {results_json}"

    def to_json(self) -> JSONDict:
        return {"inference": self.inference, "evaluate": self.evaluate}


def build_inference_command(
    gameplay_mp4: str | Path,
    predicted_mcap: str | Path,
    *,
    max_duration_seconds: int | float = 30,
) -> tuple[str, ...]:
    """Return the concrete official ``uv run inference.py`` command args."""

    return (
        "uv",
        "run",
        "inference.py",
        str(gameplay_mp4),
        str(predicted_mcap),
        "--max-duration",
        str(max_duration_seconds),
    )


def build_evaluate_command(
    ground_truth_mcap: str | Path,
    predicted_mcap: str | Path,
    results_json: str | Path,
) -> tuple[str, ...]:
    """Return the concrete official ``uv run evaluate.py`` command args."""

    return (
        "uv",
        "run",
        "evaluate.py",
        str(ground_truth_mcap),
        str(predicted_mcap),
        "--output",
        str(results_json),
    )


def shell_join(command: Iterable[str]) -> str:
    """Shell-quote a command for JSON records and run notes."""

    return shlex.join(tuple(command))


def default_offline_deviations() -> tuple[D2EDeviation, ...]:
    """Deviation table entries that explain the default offline fixture path."""

    return (
        D2EDeviation(
            deviation_id="official_evaluate_py_not_invoked_in_default_tests",
            category="official_invocation",
            status="blocked_by_offline_contract",
            severity="high",
            official_behavior="Run pinned D2E evaluate.py over ground-truth and predicted MCAP files.",
            local_behavior="Default tests call local ActionBin metrics and do not clone GitHub, load MCAP, contact Hugging Face, MLXP, or D2E data.",
            reason="Phase 0 fixture tests must be deterministic and offline; official invocation is reserved for the later real-D2E/MLXP evidence story.",
            followup="After commit/push and operational preflight, invoke uv run evaluate.py at the pinned D2E commit on a generated or real MCAP smoke fixture, or update this table with the exact blocker.",
        ),
        D2EDeviation(
            deviation_id="local_scale_ratio_formula_reimplementation",
            category="metric_formula",
            status="known_local_reimplementation",
            official_behavior="Use the scale-ratio formula in D2E evaluate.py at the pinned upstream revision for headline reports.",
            local_behavior="Fixture evaluator reports an unsigned population-stddev ratio max(std_gt,std_pred)/min(std_gt,std_pred), with NA for zero/near-zero axis scale.",
            reason="Local tests need a transparent no-dependency formula; real reports must either verify parity against evaluate.py or cite formula differences.",
            followup="Compare local fixture output against official evaluate.py on the same MCAP fixture once MCAP writer/reader compatibility is available.",
        ),
        D2EDeviation(
            deviation_id="writer_records_are_not_mcap_files",
            category="prediction_output",
            status="known_fixture_boundary",
            severity="medium",
            official_behavior="D2E inference/evaluation consumes and emits MCAP files.",
            local_behavior="Round-trip fixture wrappers reconstruct canonical events and writer-compatible dictionaries, not serialized MCAP files.",
            reason="MCAP serialization and real OWAMcap schema compatibility are dependency-gated and must be proven in a bounded real-D2E smoke story.",
            followup="Implement or enable the MCAP writer adapter, then run official evaluate.py or record the exact schema/dependency blocker.",
        ),
    )


def deviation_table_to_json(deviations: Iterable[D2EDeviation | Mapping[str, Any]]) -> list[JSONDict]:
    """Normalize deviation dataclasses/mappings to JSON dictionaries."""

    table: list[JSONDict] = []
    for deviation in deviations:
        if isinstance(deviation, D2EDeviation):
            table.append(deviation.to_json())
        else:
            table.append(dict(deviation))
    return table


def build_official_reference_record(
    *,
    upstream_repo: str = DEFAULT_UPSTREAM_REPO,
    upstream_commit: str = DEFAULT_UPSTREAM_COMMIT,
    upstream_commit_checked_at: str = DEFAULT_UPSTREAM_CHECKED_AT,
    model_id: str = DEFAULT_MODEL_ID,
    dataset_id: str = DEFAULT_DATASET_ID,
    command_templates: D2ECommandTemplates | None = None,
    deviations: Iterable[D2EDeviation | Mapping[str, Any]] | None = None,
) -> JSONDict:
    """Build the pinned official D2E reference-path record."""

    templates = command_templates or D2ECommandTemplates()
    if deviations is None:
        deviations = default_offline_deviations()
    short_commit = upstream_commit[:8]
    return {
        "schema": D2E_REFERENCE_SCHEMA,
        "reference_id": f"d2e-upstream-{short_commit}-generalist-idm-1b-reference-v1",
        "upstream_repo": upstream_repo,
        "upstream_commit": upstream_commit,
        "upstream_commit_checked_at": upstream_commit_checked_at,
        "upstream_files": {
            "evaluate_py": "evaluate.py",
            "inference_py": "inference.py",
        },
        "model_id": model_id,
        "dataset_id": dataset_id,
        "official_metric_timebase_ms": 50,
        "command_templates": templates.to_json(),
        "command_examples": {
            "inference": shell_join(build_inference_command("gameplay.mp4", "predicted.mcap", max_duration_seconds=30)),
            "evaluate": shell_join(build_evaluate_command("ground_truth.mcap", "predicted.mcap", "results.json")),
        },
        "local_evaluator": {
            "evaluator_id": LOCAL_EVALUATOR_ID,
            "metric_revision": LOCAL_METRIC_REVISION,
            "config": str(DEFAULT_EVALUATION_CONFIG),
        },
        "deviation_table": deviation_table_to_json(deviations),
        "created_by_story": EVALUATOR_STORY_ID,
        "default_tests_offline": True,
        "network_required_for_live_check": True,
        "live_check_status": "not_run_by_default_offline_tests",
        "notes": "Pinned official D2E reference path; local fixture tests do not clone, download, contact Hugging Face, or invoke MCAP evaluation.",
    }


def load_official_reference_record(path: str | Path = DEFAULT_REFERENCE_CONFIG) -> JSONDict:
    """Load a committed D2E reference record without network access."""

    with Path(path).open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)
    if payload.get("schema") != D2E_REFERENCE_SCHEMA:
        raise ValueError(f"not a D2E reference record: {path}")
    return payload


def write_official_reference_record(record: Mapping[str, Any], path: str | Path) -> Path:
    """Write a D2E reference record as stable JSON."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(stable_json_dumps(record) + "\n", encoding="utf-8")
    return output


def reference_summary(record: Mapping[str, Any]) -> JSONDict:
    """Return a compact CLI-friendly summary of a reference record."""

    templates = record.get("command_templates", {})
    deviations = tuple(record.get("deviation_table", ()))
    return {
        "story_id": record.get("created_by_story", EVALUATOR_STORY_ID),
        "status": "official_reference_record_available",
        "offline_only": bool(record.get("default_tests_offline", True)),
        "reference_id": record.get("reference_id"),
        "upstream_repo": record.get("upstream_repo"),
        "upstream_commit": record.get("upstream_commit"),
        "model_id": record.get("model_id"),
        "dataset_id": record.get("dataset_id"),
        "command_templates": dict(templates) if isinstance(templates, Mapping) else templates,
        "deviation_count": len(deviations),
        "live_check_status": record.get("live_check_status"),
    }


def stable_json_dumps(payload: Mapping[str, Any] | list[Any]) -> str:
    """Return stable JSON used by thin CLI wrappers."""

    return json.dumps(payload, indent=2, sort_keys=True)


__all__ = [
    "D2ECommandTemplates",
    "D2EDeviation",
    "D2E_REFERENCE_SCHEMA",
    "DEFAULT_DATASET_ID",
    "DEFAULT_EVALUATION_CONFIG",
    "DEFAULT_MODEL_ID",
    "DEFAULT_REFERENCE_CONFIG",
    "DEFAULT_UPSTREAM_COMMIT",
    "DEFAULT_UPSTREAM_REPO",
    "build_evaluate_command",
    "build_inference_command",
    "build_official_reference_record",
    "default_offline_deviations",
    "deviation_table_to_json",
    "load_official_reference_record",
    "reference_summary",
    "shell_join",
    "stable_json_dumps",
    "write_official_reference_record",
]
