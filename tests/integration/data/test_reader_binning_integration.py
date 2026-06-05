from __future__ import annotations

from pathlib import Path

from fdm_1_with_d2e.data import (
    KeyboardEvent,
    KeyboardEventType,
    MouseButton,
    MouseButtonEvent,
    MouseButtonEventType,
    VideoSamplingPolicy,
    bin_input_events,
    discover_labeled_recordings,
    ns_from_ms,
    sample_video_timesteps_for_bins,
    video_frame_timestamps_60fps,
)


def test_fixture_recording_discovery_binning_and_video_alignment(tmp_path: Path) -> None:
    root = tmp_path / "d2e"
    recording_dir = root / "labeled" / "fixture-game"
    recording_dir.mkdir(parents=True)
    (recording_dir / "episode_0001.mkv").write_bytes(b"tiny video placeholder")
    (recording_dir / "episode_0001.mcap").write_bytes(b"tiny mcap placeholder")

    (recording,) = discover_labeled_recordings(root)
    assert recording.recording_id == "labeled/fixture-game/episode_0001"

    binned = bin_input_events(
        start_ns=0,
        stop_ns=ns_from_ms(150),
        keyboard_events=[
            KeyboardEvent(timestamp_ns=ns_from_ms(0), key="SPACE", event_type=KeyboardEventType.DOWN),
            KeyboardEvent(timestamp_ns=ns_from_ms(75), key="SPACE", event_type=KeyboardEventType.UP),
        ],
        mouse_button_events=[
            MouseButtonEvent(
                timestamp_ns=ns_from_ms(125),
                button=MouseButton.LEFT,
                event_type=MouseButtonEventType.DOWN,
            )
        ],
        mouse_move_events=[
            {"timestamp_ns": ns_from_ms(20), "dx": 1, "dy": 2},
            {"timestamp_ns": ns_from_ms(60), "last_x": -3, "last_y": 4},
        ],
    )
    frame_timestamps = video_frame_timestamps_60fps(start_ns=0, stop_ns=ns_from_ms(150))
    video_bins = sample_video_timesteps_for_bins(frame_timestamps, binned.bins)

    assert [(item.mouse_dx, item.mouse_dy, item.sparse_event_count) for item in binned.bins] == [
        (1, 2, 1),
        (-3, 4, 1),
        (0, 0, 1),
    ]
    assert [item.action_bin_index for item in video_bins] == [0, 1, 2]
    assert all(item.policy is VideoSamplingPolicy.CAUSAL_LATEST_FRAME for item in video_bins)
    assert all(item.causal_safe for item in video_bins)
