"""Canonical 50ms action binning and 60fps video-timestep sampling."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Iterable, Mapping, Sequence
from fractions import Fraction
from typing import Any

from fdm_1_with_d2e.data.types import (
    D2E_VIDEO_FPS,
    DEFAULT_BIN_WIDTH_NS,
    NANOSECONDS_PER_MILLISECOND,
    ActionBin,
    BinningResult,
    DroppedEvent,
    EventFamily,
    KeyboardEvent,
    MouseButtonEvent,
    MouseMoveEvent,
    ScreenEvent,
    ScrollEvent,
    VideoSamplingPolicy,
    VideoTimestep,
    event_sort_key,
)


def ns_from_ms(milliseconds: int | float) -> int:
    """Convert milliseconds to nanoseconds using rounded integer precision."""

    return int(round(milliseconds * NANOSECONDS_PER_MILLISECOND))


def make_time_bins(
    start_ns: int,
    stop_ns: int,
    *,
    bin_width_ns: int = DEFAULT_BIN_WIDTH_NS,
) -> tuple[ActionBin, ...]:
    """Create non-overlapping half-open action bins covering ``[start, stop)``.

    Every returned bin has canonical ``bin_width_ns`` duration. If ``stop_ns`` is
    not aligned, the final bin extends past ``stop_ns`` for a stable 50ms action
    timestep; event assignment still treats ``stop_ns`` as exclusive.
    """

    if bin_width_ns <= 0:
        raise ValueError("bin_width_ns must be positive")
    if stop_ns < start_ns:
        raise ValueError("stop_ns must be greater than or equal to start_ns")

    bins: list[ActionBin] = []
    cursor = start_ns
    index = 0
    while cursor < stop_ns:
        bins.append(ActionBin(index=index, start_ns=cursor, end_ns=cursor + bin_width_ns))
        index += 1
        cursor += bin_width_ns
    return tuple(bins)


def normalise_mouse_delta(raw_event: MouseMoveEvent | Mapping[str, Any] | object) -> tuple[int, int, tuple[str, str]]:
    """Normalize raw mouse fields from either ``dx/dy`` or ``last_x/last_y``.

    D2E/OWAMcap snippets and the public evaluator use both naming conventions.
    This helper is intentionally strict: callers get a clear ``ValueError`` when
    neither canonical pair is present.
    """

    if isinstance(raw_event, MouseMoveEvent):
        return raw_event.dx, raw_event.dy, raw_event.source_fields

    if _has_fields(raw_event, "dx", "dy"):
        return int(_get_field(raw_event, "dx")), int(_get_field(raw_event, "dy")), ("dx", "dy")
    if _has_fields(raw_event, "last_x", "last_y"):
        return (
            int(_get_field(raw_event, "last_x")),
            int(_get_field(raw_event, "last_y")),
            ("last_x", "last_y"),
        )
    raise ValueError("raw mouse event must expose either dx/dy or last_x/last_y fields")


def mouse_move_event_from_raw(
    raw_event: MouseMoveEvent | Mapping[str, Any] | object,
    *,
    timestamp_ns: int | None = None,
) -> MouseMoveEvent:
    """Create a canonical ``MouseMoveEvent`` from raw decoded data."""

    if isinstance(raw_event, MouseMoveEvent):
        return raw_event
    if timestamp_ns is None:
        timestamp_ns = _extract_timestamp_ns(raw_event)
    dx, dy, source_fields = normalise_mouse_delta(raw_event)
    return MouseMoveEvent(timestamp_ns=timestamp_ns, dx=dx, dy=dy, source_fields=source_fields)


def bin_input_events(
    *,
    start_ns: int,
    stop_ns: int,
    keyboard_events: Iterable[KeyboardEvent] = (),
    mouse_button_events: Iterable[MouseButtonEvent] = (),
    scroll_events: Iterable[ScrollEvent] = (),
    mouse_move_events: Iterable[MouseMoveEvent | Mapping[str, Any] | object] = (),
    screen_events: Iterable[ScreenEvent] = (),
    bin_width_ns: int = DEFAULT_BIN_WIDTH_NS,
) -> BinningResult:
    """Assign canonical events to 50ms bins and aggregate raw mouse deltas."""

    empty_bins = make_time_bins(start_ns, stop_ns, bin_width_ns=bin_width_ns)
    mouse_dx = [0 for _ in empty_bins]
    mouse_dy = [0 for _ in empty_bins]
    keyboard_by_bin: list[list[KeyboardEvent]] = [[] for _ in empty_bins]
    mouse_button_by_bin: list[list[MouseButtonEvent]] = [[] for _ in empty_bins]
    scroll_by_bin: list[list[ScrollEvent]] = [[] for _ in empty_bins]
    screen_by_bin: list[list[ScreenEvent]] = [[] for _ in empty_bins]
    dropped: list[DroppedEvent] = []

    for raw_mouse_event in mouse_move_events:
        event = mouse_move_event_from_raw(raw_mouse_event)
        index = _event_bin_index(event.timestamp_ns, start_ns, stop_ns, bin_width_ns, len(empty_bins))
        if index is None:
            dropped.append(_dropped_event(event.timestamp_ns, EventFamily.MOUSE_MOVE, start_ns, stop_ns))
            continue
        mouse_dx[index] += event.dx
        mouse_dy[index] += event.dy

    for event in keyboard_events:
        index = _event_bin_index(event.timestamp_ns, start_ns, stop_ns, bin_width_ns, len(empty_bins))
        if index is None:
            dropped.append(_dropped_event(event.timestamp_ns, event.family, start_ns, stop_ns))
        else:
            keyboard_by_bin[index].append(event)

    for event in mouse_button_events:
        index = _event_bin_index(event.timestamp_ns, start_ns, stop_ns, bin_width_ns, len(empty_bins))
        if index is None:
            dropped.append(_dropped_event(event.timestamp_ns, event.family, start_ns, stop_ns))
        else:
            mouse_button_by_bin[index].append(event)

    for event in scroll_events:
        index = _event_bin_index(event.timestamp_ns, start_ns, stop_ns, bin_width_ns, len(empty_bins))
        if index is None:
            dropped.append(_dropped_event(event.timestamp_ns, event.family, start_ns, stop_ns))
        else:
            scroll_by_bin[index].append(event)

    for event in screen_events:
        index = _event_bin_index(event.timestamp_ns, start_ns, stop_ns, bin_width_ns, len(empty_bins))
        if index is None:
            dropped.append(_dropped_event(event.timestamp_ns, event.family, start_ns, stop_ns))
        else:
            screen_by_bin[index].append(event)

    bins = tuple(
        ActionBin(
            index=empty_bin.index,
            start_ns=empty_bin.start_ns,
            end_ns=empty_bin.end_ns,
            mouse_dx=mouse_dx[empty_bin.index],
            mouse_dy=mouse_dy[empty_bin.index],
            keyboard_events=tuple(sorted(keyboard_by_bin[empty_bin.index], key=event_sort_key)),
            mouse_button_events=tuple(sorted(mouse_button_by_bin[empty_bin.index], key=event_sort_key)),
            scroll_events=tuple(sorted(scroll_by_bin[empty_bin.index], key=event_sort_key)),
            screen_events=tuple(sorted(screen_by_bin[empty_bin.index], key=event_sort_key)),
        )
        for empty_bin in empty_bins
    )
    return BinningResult(
        bins=bins,
        dropped_events=tuple(dropped),
        start_ns=start_ns,
        stop_ns=stop_ns,
        bin_width_ns=bin_width_ns,
    )


def video_frame_timestamps_60fps(
    *,
    start_ns: int,
    stop_ns: int,
    fps: int = D2E_VIDEO_FPS,
) -> tuple[int, ...]:
    """Return ideal source-frame timestamps for a fixed-FPS video span."""

    if fps <= 0:
        raise ValueError("fps must be positive")
    if stop_ns < start_ns:
        raise ValueError("stop_ns must be greater than or equal to start_ns")
    period = Fraction(1_000_000_000, fps)
    timestamps: list[int] = []
    index = 0
    while True:
        offset = int(period * index + Fraction(1, 2))
        timestamp = start_ns + offset
        if timestamp >= stop_ns:
            break
        timestamps.append(timestamp)
        index += 1
    return tuple(timestamps)


def sample_video_timesteps_for_bins(
    frame_timestamps_ns: Sequence[int],
    action_bins: Sequence[ActionBin],
    *,
    policy: VideoSamplingPolicy = VideoSamplingPolicy.CAUSAL_LATEST_FRAME,
    source_fps: int = D2E_VIDEO_FPS,
) -> tuple[VideoTimestep, ...]:
    """Map source frame timestamps to one visual timestep per action bin."""

    frames = tuple(int(timestamp) for timestamp in frame_timestamps_ns)
    if tuple(sorted(frames)) != frames:
        raise ValueError("frame_timestamps_ns must be sorted in nondecreasing order")

    timesteps: list[VideoTimestep] = []
    for action_bin in action_bins:
        if policy is VideoSamplingPolicy.CAUSAL_LATEST_FRAME:
            selected = _select_causal_latest(frames, action_bin.start_ns)
            causal_safe = True
            metadata = {
                "policy_label": "latest source frame timestamp at or before action bin start",
                "allowed_max_source_timestamp_ns": action_bin.start_ns,
            }
        elif policy is VideoSamplingPolicy.WITHIN_BIN_FRAMES:
            selected = _select_within_bin(frames, action_bin.start_ns, action_bin.end_ns)
            causal_safe = False
            metadata = {
                "policy_label": "all source frames inside the target action bin; shift before FDM use",
                "requires_fdm_reindex": True,
            }
        elif policy is VideoSamplingPolicy.CENTER_FRAME_WITHIN_BIN:
            selected = _select_center_frame(frames, action_bin.start_ns, action_bin.end_ns)
            causal_safe = False
            metadata = {
                "policy_label": "single source frame nearest the target action-bin center; shift before FDM use",
                "requires_fdm_reindex": True,
            }
        else:
            raise ValueError(f"unsupported video sampling policy: {policy}")

        selected_timestamps = tuple(frames[index] for index in selected)
        timesteps.append(
            VideoTimestep(
                action_bin_index=action_bin.index,
                action_start_ns=action_bin.start_ns,
                action_end_ns=action_bin.end_ns,
                policy=policy,
                source_frame_indices=selected,
                source_frame_timestamps_ns=selected_timestamps,
                source_span_start_ns=min(selected_timestamps) if selected_timestamps else None,
                source_span_end_ns=max(selected_timestamps) if selected_timestamps else None,
                decision_time_ns=action_bin.start_ns,
                causal_safe=causal_safe
                and all(timestamp <= action_bin.start_ns for timestamp in selected_timestamps),
                source_fps=source_fps,
                metadata=metadata,
            )
        )
    return tuple(timesteps)


def _event_bin_index(
    timestamp_ns: int,
    start_ns: int,
    stop_ns: int,
    bin_width_ns: int,
    bin_count: int,
) -> int | None:
    if timestamp_ns < start_ns or timestamp_ns >= stop_ns:
        return None
    index = (timestamp_ns - start_ns) // bin_width_ns
    if index < 0 or index >= bin_count:
        return None
    return int(index)


def _dropped_event(timestamp_ns: int, family: EventFamily, start_ns: int, stop_ns: int) -> DroppedEvent:
    reason = "before_start" if timestamp_ns < start_ns else "at_or_after_stop"
    return DroppedEvent(timestamp_ns=timestamp_ns, family=family, reason=reason)


def _has_fields(raw_event: Mapping[str, Any] | object, first: str, second: str) -> bool:
    return _field_exists(raw_event, first) and _field_exists(raw_event, second)


def _field_exists(raw_event: Mapping[str, Any] | object, field_name: str) -> bool:
    if isinstance(raw_event, Mapping):
        return field_name in raw_event
    return hasattr(raw_event, field_name)


def _get_field(raw_event: Mapping[str, Any] | object, field_name: str) -> Any:
    if isinstance(raw_event, Mapping):
        return raw_event[field_name]
    return getattr(raw_event, field_name)


def _extract_timestamp_ns(raw_event: Mapping[str, Any] | object) -> int:
    for field_name in ("timestamp_ns", "log_time_ns", "publish_time_ns"):
        if _field_exists(raw_event, field_name):
            return int(_get_field(raw_event, field_name))
    raise ValueError("raw event timestamp_ns must be provided explicitly or as timestamp_ns/log_time_ns")


def _select_causal_latest(frames: Sequence[int], decision_time_ns: int) -> tuple[int, ...]:
    index = bisect_right(frames, decision_time_ns) - 1
    if index < 0:
        return ()
    return (index,)


def _select_within_bin(frames: Sequence[int], start_ns: int, end_ns: int) -> tuple[int, ...]:
    left = bisect_left(frames, start_ns)
    right = bisect_left(frames, end_ns)
    return tuple(range(left, right))


def _select_center_frame(frames: Sequence[int], start_ns: int, end_ns: int) -> tuple[int, ...]:
    inside = _select_within_bin(frames, start_ns, end_ns)
    if not inside:
        return ()
    center_ns = start_ns + (end_ns - start_ns) // 2
    return (min(inside, key=lambda index: (abs(frames[index] - center_ns), frames[index])),)
