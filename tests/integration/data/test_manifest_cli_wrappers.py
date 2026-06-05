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
