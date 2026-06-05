from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from fdm_1_with_d2e.data import (
    ActionBin,
    DatasetArtifactPathError,
    KeyboardEvent,
    KeyboardEventType,
    MouseButton,
    MouseButtonEvent,
    MouseButtonEventType,
    ScrollEvent,
    assert_artifact_path_outside_dataset_root,
    build_action_distribution_manifest,
    build_dataset_manifest,
    build_held_out_game_split_manifest,
    build_scale_manifest,
    build_train_val_test_split_manifest,
    discover_labeled_recordings,
    ns_from_ms,
    stable_json_dumps,
)
from fdm_1_with_d2e.tokenization import ActionTokenizer


def _touch(path: Path, data: bytes = b"fixture") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _fixture_dataset(tmp_path: Path, games: tuple[str, ...] = ("alpha", "beta"), per_game: int = 5) -> Path:
    root = tmp_path / "d2e"
    for game in games:
        for index in range(per_game):
            stem = f"run_{index:02d}"
            _touch(root / "labeled" / game / f"{stem}.mkv", f"video-{game}-{index}".encode())
            _touch(root / "labeled" / game / f"{stem}.mcap", f"mcap-{game}-{index}".encode())
    return root


def test_dataset_manifest_records_sizes_checksums_durations_and_stable_json(tmp_path: Path) -> None:
    root = _fixture_dataset(tmp_path, games=("zeta", "alpha"), per_game=1)
    recordings = discover_labeled_recordings(root)
    durations = {"labeled/alpha/run_00": {"duration_ns": ns_from_ms(125)}}

    manifest = build_dataset_manifest(
        recordings,
        dataset_root=root,
        include_checksums=True,
        duration_metadata=durations,
    )
    repeated = build_dataset_manifest(
        reversed(recordings),
        dataset_root=root,
        include_checksums=True,
        duration_metadata=durations,
    )

    assert manifest == repeated
    assert manifest["schema"] == "schemas/dataset_manifest.schema.json"
    assert manifest["dataset_root"] == root.as_posix()
    assert manifest["recording_count"] == 2
    assert [entry["recording_id"] for entry in manifest["recordings"]] == [
        "labeled/alpha/run_00",
        "labeled/zeta/run_00",
    ]

    first = manifest["recordings"][0]
    assert first["video_path"] == "labeled/alpha/run_00.mkv"
    assert first["mcap_path"] == "labeled/alpha/run_00.mcap"
    assert first["video_size_bytes"] == len(b"video-alpha-0")
    assert first["mcap_size_bytes"] == len(b"mcap-alpha-0")
    assert first["video_sha256"] == hashlib.sha256(b"video-alpha-0").hexdigest()
    assert first["duration_ns"] == ns_from_ms(125)
    assert first["duration_seconds"] == 0.125
    assert first["timebase_bin_count"] == 3
    assert stable_json_dumps(manifest) == stable_json_dumps(repeated)


def test_split_heldout_and_scale_manifests_are_deterministic_and_grouped(tmp_path: Path) -> None:
    root = _fixture_dataset(tmp_path)
    manifest = build_dataset_manifest(discover_labeled_recordings(root), dataset_root=root)

    split = build_train_val_test_split_manifest(manifest, seed=123)
    repeated = build_train_val_test_split_manifest(manifest, seed=123)

    assert split == repeated
    assert split["counts"] == {"train": 6, "validation": 2, "test": 2, "held_out_test": 0}
    assert set(split["train"]).isdisjoint(split["validation"])
    assert set(split["train"]).isdisjoint(split["test"])
    assert set(split["validation"]).isdisjoint(split["test"])
    assert set(split["train"] + split["validation"] + split["test"]) == {
        entry["recording_id"] for entry in manifest["recordings"]
    }
    assert split["per_game_counts"] == {
        "alpha": {"train": 3, "validation": 1, "test": 1},
        "beta": {"train": 3, "validation": 1, "test": 1},
    }

    heldout = build_held_out_game_split_manifest(manifest, ["beta"], seed=123)
    assert heldout["held_out_games"] == ["beta"]
    assert heldout["held_out_test"] == [f"labeled/beta/run_{index:02d}" for index in range(5)]
    assert all("/beta/" not in recording_id for recording_id in heldout["train"])
    with pytest.raises(ValueError, match="held-out games not present"):
        build_held_out_game_split_manifest(manifest, ["missing-game"])

    scales = build_scale_manifest(split, dataset_manifest=manifest, optional_percentages=(25,), seed=123)
    assert set(scales["scales"]["10_percent"]).issubset(scales["scales"]["50_percent"])
    assert set(scales["scales"]["50_percent"]).issubset(scales["scales"]["100_percent"])
    assert len(scales["scales"]["10_percent"]) == 2  # one per game because scaling is game-stratified.
    assert len(scales["scales"]["25_percent"]) == 2
    assert len(scales["scales"]["50_percent"]) == 4
    assert scales["scales"]["100_percent"] == sorted(split["train"])


def test_scale_manifest_optional_percentages_are_nested_by_game(tmp_path: Path) -> None:
    root = _fixture_dataset(tmp_path, games=("alpha", "beta"), per_game=20)
    manifest = build_dataset_manifest(discover_labeled_recordings(root), dataset_root=root)
    split = build_train_val_test_split_manifest(manifest, seed=123)

    scales = build_scale_manifest(split, dataset_manifest=manifest, optional_percentages=(5,), seed=123)

    five = set(scales["scales"]["5_percent"])
    ten = set(scales["scales"]["10_percent"])
    fifty = set(scales["scales"]["50_percent"])
    full = set(scales["scales"]["100_percent"])
    assert five <= ten <= fifty <= full
    assert full == set(split["train"])


def test_artifact_guard_rejects_dataset_tree_outputs(tmp_path: Path) -> None:
    root = tmp_path / "d2e"
    root.mkdir()

    assert_artifact_path_outside_dataset_root(tmp_path / "outputs" / "manifest.json", root)
    with pytest.raises(DatasetArtifactPathError, match="read-only dataset root"):
        assert_artifact_path_outside_dataset_root(root / "labeled" / "manifest.json", root)


def test_action_distribution_summarizes_canonical_and_tokenized_bins(tmp_path: Path) -> None:
    root = _fixture_dataset(tmp_path, games=("alpha", "beta"), per_game=1)
    manifest = build_dataset_manifest(discover_labeled_recordings(root), dataset_root=root)
    tokenizer = ActionTokenizer()

    canonical_bins = (
        ActionBin(index=0, start_ns=0, end_ns=ns_from_ms(50)),
        ActionBin(
            index=1,
            start_ns=ns_from_ms(50),
            end_ns=ns_from_ms(100),
            mouse_dx=3,
            mouse_dy=4,
            keyboard_events=(KeyboardEvent(ns_from_ms(60), "SPACE", KeyboardEventType.DOWN),),
            scroll_events=(ScrollEvent(ns_from_ms(65), delta_x=1, delta_y=-1),),
        ),
        ActionBin(
            index=2,
            start_ns=ns_from_ms(100),
            end_ns=ns_from_ms(150),
            mouse_button_events=(
                MouseButtonEvent(ns_from_ms(110), MouseButton.LEFT, MouseButtonEventType.DOWN),
            ),
        ),
    )
    overflow_source = ActionBin(
        index=0,
        start_ns=0,
        end_ns=ns_from_ms(50),
        keyboard_events=tuple(
            KeyboardEvent(ns_from_ms(1 + index), chr(ord("A") + index), KeyboardEventType.DOWN)
            for index in range(9)
        ),
    )
    tokenized_overflow = tokenizer.tokenize_bins((overflow_source,))

    distribution = build_action_distribution_manifest(
        manifest,
        {
            "labeled/alpha/run_00": canonical_bins,
            "labeled/beta/run_00": tokenized_overflow,
        },
        tokenizer=tokenizer,
    )

    alpha = distribution["summaries"][0]
    beta = distribution["summaries"][1]
    assert alpha["game"] == "alpha"
    assert alpha["bin_count"] == 3
    assert alpha["no_op_bin_count"] == 1
    assert alpha["no_op_rate"] == pytest.approx(1 / 3)
    assert alpha["event_count"] == 5
    assert alpha["event_family_counts"] == {
        "keyboard": 1,
        "mouse_button": 1,
        "mouse_move": 1,
        "scroll": 2,
    }
    assert alpha["raw_mouse_magnitude_summary"]["max_l2"] == 5.0

    assert beta["game"] == "beta"
    assert beta["overflow_bin_count"] == 1
    assert beta["overflow_event_count"] == 2
    assert beta["overflow_rate"] == 1.0
    assert distribution["totals"]["recording_count"] == 2
    assert distribution["totals"]["bin_count"] == 4
