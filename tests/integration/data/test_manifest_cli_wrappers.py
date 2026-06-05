from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fdm_1_with_d2e.data import ns_from_ms

REPO_ROOT = Path(__file__).resolve().parents[3]


def _touch(path: Path, data: bytes = b"fixture") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_manifest_and_action_distribution_cli_wrappers_use_package_builders(tmp_path: Path) -> None:
    root = tmp_path / "d2e"
    _touch(root / "labeled" / "game" / "run_00.mkv", b"video")
    _touch(root / "labeled" / "game" / "run_00.mcap", b"mcap")
    output_dir = tmp_path / "outputs"
    dataset_manifest_path = output_dir / "dataset.json"
    split_manifest_path = output_dir / "split.json"
    scale_manifest_path = output_dir / "scale.json"

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "build_d2e_manifest.py"),
            "--dataset-root",
            str(root),
            "--output",
            str(dataset_manifest_path),
            "--split-output",
            str(split_manifest_path),
            "--scale-output",
            str(scale_manifest_path),
            "--optional-scale",
            "5",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    payload = json.loads(result.stdout)
    assert result.stderr == ""
    assert payload["dataset_manifest"]["recording_count"] == 1
    assert dataset_manifest_path.exists()
    assert split_manifest_path.exists()
    assert scale_manifest_path.exists()

    bins_path = output_dir / "bins.json"
    bins_path.write_text(
        json.dumps(
            {
                "recording_bins": {
                    "labeled/game/run_00": [
                        {
                            "index": 0,
                            "start_ns": 0,
                            "end_ns": ns_from_ms(50),
                            "mouse_dx": 0,
                            "mouse_dy": 0,
                        },
                        {
                            "index": 1,
                            "start_ns": ns_from_ms(50),
                            "end_ns": ns_from_ms(100),
                            "mouse_dx": 2,
                            "mouse_dy": -1,
                            "keyboard_events": [
                                {
                                    "timestamp_ns": ns_from_ms(60),
                                    "key": "W",
                                    "event_type": "down",
                                }
                            ],
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    distribution_path = output_dir / "action_distribution.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "summarize_action_distribution.py"),
            "--dataset-manifest",
            str(dataset_manifest_path),
            "--bins-json",
            str(bins_path),
            "--output",
            str(distribution_path),
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    payload = json.loads(result.stdout)
    assert result.stderr == ""
    summary = payload["action_distribution"]["summaries"][0]
    assert summary["game"] == "game"
    assert summary["bin_count"] == 2
    assert summary["no_op_rate"] == 0.5
    assert distribution_path.exists()

    records_path = output_dir / "records.json"
    records_path.write_text(
        json.dumps(
            {
                "recording_records": {
                    "labeled/game/run_00": [
                        {
                            "topic": "screen",
                            "log_time_ns": 0,
                            "data": {"media_ref": {"pts_ns": 0}, "shape": [480, 854, 3]},
                        },
                        {
                            "topic": "keyboard",
                            "log_time_ns": ns_from_ms(10),
                            "data": {"event_type": "press", "vk": 87},
                        },
                        {
                            "topic": "mouse/raw",
                            "log_time_ns": ns_from_ms(20),
                            "data": {"last_x": 2, "last_y": -1},
                        },
                        {
                            "topic": "mouse",
                            "log_time_ns": ns_from_ms(25),
                            "data": {"event_type": "move", "x": 101, "y": 202},
                        },
                        {
                            "topic": "mouse",
                            "log_time_ns": ns_from_ms(60),
                            "data": {"event_type": "click", "button": "left", "pressed": True},
                        },
                        {
                            "topic": "mouse",
                            "log_time_ns": ns_from_ms(75),
                            "data": {"event_type": "scroll", "dx": 0, "dy": -1},
                        },
                        {
                            "topic": "screen",
                            "log_time_ns": ns_from_ms(100),
                            "data": {"media_ref": {"pts_ns": ns_from_ms(100)}, "shape": [480, 854, 3]},
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    decoded_distribution_path = output_dir / "decoded_action_distribution.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "summarize_action_distribution.py"),
            "--dataset-manifest",
            str(dataset_manifest_path),
            "--records-json",
            str(records_path),
            "--recording-id",
            "labeled/game/run_00",
            "--one-per-game",
            "--max-recordings",
            "1",
            "--output",
            str(decoded_distribution_path),
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    payload = json.loads(result.stdout)
    assert result.stderr == ""
    decoded_distribution = payload["action_distribution"]
    decoded_summary = decoded_distribution["summaries"][0]
    source_summary = decoded_distribution["source_mcap_json_summary"]
    assert decoded_summary["event_family_counts"] == {
        "keyboard": 1,
        "mouse_button": 1,
        "mouse_move": 1,
        "scroll": 1,
    }
    assert source_summary["source"] == "decoded_records_json"
    assert source_summary["selected_recording_ids"] == ["labeled/game/run_00"]
    assert source_summary["recordings"]["labeled/game/run_00"]["screen_frame_count"] == 2
    assert source_summary["recordings"]["labeled/game/run_00"]["ignored_absolute_mouse_move_count"] == 1
    assert decoded_distribution_path.exists()
