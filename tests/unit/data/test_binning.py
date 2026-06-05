from __future__ import annotations

from types import SimpleNamespace

from fdm_1_with_d2e.data import (
    DEFAULT_BIN_WIDTH_NS,
    KeyboardEvent,
    KeyboardEventType,
    MouseButton,
    MouseButtonEvent,
    MouseButtonEventType,
    ScrollDirection,
    ScrollEvent,
    VideoSamplingPolicy,
    bin_input_events,
    make_time_bins,
    mouse_move_event_from_raw,
    normalise_mouse_delta,
    ns_from_ms,
    sample_video_timesteps_for_bins,
    video_frame_timestamps_60fps,
)


def test_make_time_bins_are_half_open_50ms_intervals() -> None:
    bins = make_time_bins(ns_from_ms(0), ns_from_ms(120))

    assert [(item.index, item.start_ns, item.end_ns) for item in bins] == [
        (0, 0, DEFAULT_BIN_WIDTH_NS),
        (1, DEFAULT_BIN_WIDTH_NS, 2 * DEFAULT_BIN_WIDTH_NS),
        (2, 2 * DEFAULT_BIN_WIDTH_NS, 3 * DEFAULT_BIN_WIDTH_NS),
    ]


def test_bin_input_events_assigns_boundaries_and_sums_mouse_deltas() -> None:
    result = bin_input_events(
        start_ns=0,
        stop_ns=ns_from_ms(100),
        keyboard_events=[
            KeyboardEvent(timestamp_ns=0, key="A", event_type=KeyboardEventType.DOWN),
            KeyboardEvent(timestamp_ns=ns_from_ms(50), key="A", event_type=KeyboardEventType.UP),
        ],
        mouse_button_events=[
            MouseButtonEvent(
                timestamp_ns=ns_from_ms(50) - 1,
                button=MouseButton.LEFT,
                event_type=MouseButtonEventType.DOWN,
            )
        ],
        scroll_events=[
            ScrollEvent(timestamp_ns=ns_from_ms(100), delta_y=1),
        ],
        mouse_move_events=[
            {"timestamp_ns": ns_from_ms(1), "dx": 2, "dy": -1},
            {"timestamp_ns": ns_from_ms(10), "last_x": 3, "last_y": -5},
            SimpleNamespace(timestamp_ns=ns_from_ms(55), dx=-4, dy=8),
        ],
    )

    assert len(result.bins) == 2
    first, second = result.bins
    assert first.mouse_dx == 5
    assert first.mouse_dy == -6
    assert [event.key for event in first.keyboard_events] == ["A"]
    assert [event.event_type for event in first.keyboard_events] == [KeyboardEventType.DOWN]
    assert [event.button for event in first.mouse_button_events] == [MouseButton.LEFT]

    assert second.mouse_dx == -4
    assert second.mouse_dy == 8
    assert [event.event_type for event in second.keyboard_events] == [KeyboardEventType.UP]
    assert second.scroll_events == ()

    # Timestamp equal to stop_ns is outside the requested range.
    assert result.dropped_event_count == 1
    assert result.dropped_events[0].timestamp_ns == ns_from_ms(100)
    assert result.dropped_events[0].reason == "at_or_after_stop"


def test_raw_mouse_normalization_accepts_dx_dy_and_last_x_last_y() -> None:
    assert normalise_mouse_delta({"dx": 7, "dy": -8}) == (7, -8, ("dx", "dy"))
    assert normalise_mouse_delta(SimpleNamespace(last_x=-2, last_y=9)) == (
        -2,
        9,
        ("last_x", "last_y"),
    )

    event = mouse_move_event_from_raw(
        {"timestamp_ns": ns_from_ms(25), "last_x": 4, "last_y": -6}
    )
    assert event.timestamp_ns == ns_from_ms(25)
    assert event.dx == 4
    assert event.dy == -6
    assert event.source_fields == ("last_x", "last_y")


def test_sparse_discrete_events_are_sorted_by_timestamp_and_family() -> None:
    result = bin_input_events(
        start_ns=0,
        stop_ns=ns_from_ms(50),
        keyboard_events=[
            KeyboardEvent(timestamp_ns=ns_from_ms(20), key="Z", event_type=KeyboardEventType.DOWN),
            KeyboardEvent(timestamp_ns=ns_from_ms(10), key="A", event_type=KeyboardEventType.DOWN),
        ],
        mouse_button_events=[
            MouseButtonEvent(
                timestamp_ns=ns_from_ms(20),
                button=MouseButton.RIGHT,
                event_type=MouseButtonEventType.UP,
            )
        ],
        scroll_events=[
            ScrollEvent(timestamp_ns=ns_from_ms(15), delta_y=-1),
        ],
    )

    discrete = result.bins[0].discrete_events

    assert [(event.family.value, event.timestamp_ns) for event in discrete] == [
        ("keyboard", ns_from_ms(10)),
        ("scroll", ns_from_ms(15)),
        ("keyboard", ns_from_ms(20)),
        ("mouse_button", ns_from_ms(20)),
    ]
    assert result.bins[0].scroll_events[0].directions == (ScrollDirection.DOWN,)


def test_video_sampler_maps_60fps_frames_to_causal_50ms_timesteps() -> None:
    bins = make_time_bins(0, ns_from_ms(150))
    frame_timestamps = video_frame_timestamps_60fps(start_ns=0, stop_ns=ns_from_ms(150))

    timesteps = sample_video_timesteps_for_bins(frame_timestamps, bins)

    assert len(timesteps) == len(bins)
    assert [item.source_frame_timestamps_ns for item in timesteps] == [
        (ns_from_ms(0),),
        (ns_from_ms(50),),
        (ns_from_ms(100),),
    ]
    assert all(item.policy is VideoSamplingPolicy.CAUSAL_LATEST_FRAME for item in timesteps)
    assert all(item.causal_safe for item in timesteps)
    assert all(item.source_span_end_ns <= item.decision_time_ns for item in timesteps)


def test_video_sampler_records_noncausal_within_bin_span_metadata() -> None:
    bins = make_time_bins(0, ns_from_ms(50))
    frame_timestamps = video_frame_timestamps_60fps(start_ns=0, stop_ns=ns_from_ms(50))

    (timestep,) = sample_video_timesteps_for_bins(
        frame_timestamps,
        bins,
        policy=VideoSamplingPolicy.WITHIN_BIN_FRAMES,
    )

    assert timestep.source_frame_timestamps_ns == (
        ns_from_ms(0),
        16_666_667,
        33_333_333,
    )
    assert timestep.source_span_start_ns == 0
    assert timestep.source_span_end_ns == 33_333_333
    assert timestep.causal_safe is False
    assert timestep.metadata is not None
    assert timestep.metadata["requires_fdm_reindex"] is True
