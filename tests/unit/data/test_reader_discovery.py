from __future__ import annotations

from pathlib import Path

import pytest

from fdm_1_with_d2e.data.reader import (
    OWAMcapReader,
    OptionalOWAMcapDependencyError,
    discover_labeled_recordings,
    find_unpaired_labeled_files,
)


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fixture")


def test_discover_labeled_recordings_returns_deterministic_pairs_without_content_reads(
    tmp_path: Path,
) -> None:
    root = tmp_path / "d2e"
    # Create intentionally unsorted paths.
    _touch(root / "labeled" / "z-game" / "run_2.mcap")
    _touch(root / "labeled" / "z-game" / "run_2.mkv")
    _touch(root / "labeled" / "a-game" / "run_1.mkv")
    _touch(root / "labeled" / "a-game" / "run_1.mcap")
    _touch(root / "labeled" / "a-game" / "orphan_video.mkv")
    _touch(root / "labeled" / "z-game" / "orphan_events.mcap")
    _touch(root / "labeled" / ".source-metadata" / "ignored.mkv")
    _touch(root / "labeled" / ".source-metadata" / "ignored.mcap")
    _touch(root / "unlabeled" / "a-game" / "video_only.mkv")

    recordings = discover_labeled_recordings(root)

    assert [recording.recording_id for recording in recordings] == [
        "labeled/a-game/run_1",
        "labeled/z-game/run_2",
    ]
    assert [recording.relative_video_path.as_posix() for recording in recordings] == [
        "labeled/a-game/run_1.mkv",
        "labeled/z-game/run_2.mkv",
    ]
    assert [recording.relative_mcap_path.as_posix() for recording in recordings] == [
        "labeled/a-game/run_1.mcap",
        "labeled/z-game/run_2.mcap",
    ]


def test_find_unpaired_labeled_files_ignores_source_metadata(tmp_path: Path) -> None:
    root = tmp_path / "d2e"
    _touch(root / "labeled" / "game" / "paired.mkv")
    _touch(root / "labeled" / "game" / "paired.mcap")
    _touch(root / "labeled" / "game" / "missing_events.mkv")
    _touch(root / "labeled" / "game" / "missing_video.mcap")
    _touch(root / "labeled" / ".source-metadata" / "ignored.mkv")

    unpaired = find_unpaired_labeled_files(root)

    assert [path.relative_to(root).as_posix() for path in unpaired] == [
        "labeled/game/missing_events.mkv",
        "labeled/game/missing_video.mcap",
    ]


def test_optional_owamcap_reader_reports_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force the dependency gate to be deterministic even if a developer machine
    # happens to have the MCAP package installed.
    monkeypatch.setattr(
        "fdm_1_with_d2e.data.reader._REQUIRED_OWAMCAP_MODULES",
        ("definitely_missing_fdm_d2e_mcap_reader",),
    )

    with pytest.raises(OptionalOWAMcapDependencyError) as error:
        OWAMcapReader("fixture.mcap")

    assert "OWAMcap reading requires optional MCAP dependencies" in str(error.value)
    assert error.value.missing_modules == ("definitely_missing_fdm_d2e_mcap_reader",)
