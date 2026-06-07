"""Per-bin temporal sanity artifacts for real D2E action windows."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

from fdm_1_with_d2e.data.manifests import assert_artifact_path_outside_dataset_root, stable_json_dumps, write_json_artifact
from fdm_1_with_d2e.data.mcap_json import (
    DecodedMcapJsonActions,
    bin_decoded_mcap_json_actions,
    read_d2e_json_mcap_actions,
)
from fdm_1_with_d2e.data.types import (
    DEFAULT_BIN_WIDTH_NS,
    ActionBin,
    KeyboardEvent,
    KeyboardEventType,
    MouseButtonEvent,
    ScrollEvent,
    event_sort_key,
)
from fdm_1_with_d2e.tokenization.actions import ActionTokenizer, TokenizedActionBin, tokenize_action_bins

TEMPORAL_SANITY_SCHEMA = "fdm_1_with_d2e.temporal_sanity_window.v1"
TEMPORAL_SANITY_STORY_ID = "post-phase0-temporal-sanity"


@dataclass(frozen=True, slots=True)
class TemporalWindowSelection:
    """Resolved 50ms-bin window for temporal sanity export."""

    start_bin: int
    length_bins: int
    reason: str
    score: float

    @property
    def stop_bin_exclusive(self) -> int:
        return self.start_bin + self.length_bins


def export_temporal_sanity_window(
    *,
    video_path: str | Path | None,
    mcap_path: str | Path,
    output_dir: str | Path,
    dataset_root: str | Path | None = None,
    duration_seconds: float = 10.0,
    start_bin: int | None = None,
    start_seconds: float | None = None,
    write_frames: bool = True,
    frame_overlay: bool = True,
    tokenizer: ActionTokenizer | None = None,
) -> dict[str, Any]:
    """Export one real-D2E per-bin sanity window with tokens and key replay state.

    The function writes ``summary.json`` and ``bins.jsonl``.  When ``write_frames``
    is true it also writes one PNG per 50ms bin under ``frames/`` using OpenCV.
    Outputs are guarded to stay outside the dataset root.
    """

    resolved_output = Path(output_dir)
    assert_artifact_path_outside_dataset_root(resolved_output, dataset_root)
    resolved_output.mkdir(parents=True, exist_ok=True)

    decoded = read_d2e_json_mcap_actions(mcap_path)
    bins, span = bins_for_screen_span(decoded)
    if not bins:
        raise ValueError(f"no 50ms bins decoded from {mcap_path}")

    length_bins = max(1, int(math.ceil(float(duration_seconds) * 1_000_000_000 / DEFAULT_BIN_WIDTH_NS)))
    selection = resolve_window_selection(
        bins,
        length_bins=length_bins,
        start_bin=start_bin,
        start_seconds=start_seconds,
    )
    window_bins = bins[selection.start_bin : selection.stop_bin_exclusive]
    resolved_tokenizer = tokenizer or ActionTokenizer()
    tokenized = tokenize_action_bins(window_bins, tokenizer=resolved_tokenizer)
    replay = replay_keyboard_state(bins, selection.start_bin, selection.stop_bin_exclusive)

    frame_records: dict[int, dict[str, Any]] = {}
    if write_frames:
        if video_path is None:
            raise ValueError("video_path is required when write_frames=True")
        frame_records = write_window_frames(
            video_path=Path(video_path),
            output_dir=resolved_output / "frames",
            bins=window_bins,
            first_screen_ns=span["start_ns"],
            frame_overlay=frame_overlay,
        )

    bins_path = resolved_output / "bins.jsonl"
    bin_rows = []
    with bins_path.open("w", encoding="utf-8") as file_obj:
        for action_bin, tokenized_bin in zip(window_bins, tokenized.bins, strict=True):
            row = temporal_bin_record(
                action_bin,
                tokenized_bin,
                key_state=replay["bin_states"][str(action_bin.index)],
                frame=frame_records.get(action_bin.index),
            )
            bin_rows.append(row)
            file_obj.write(stable_json_dumps(row))
            file_obj.write("\n")

    summary = {
        "schema": TEMPORAL_SANITY_SCHEMA,
        "story_id": TEMPORAL_SANITY_STORY_ID,
        "video_path": None if video_path is None else str(video_path),
        "mcap_path": str(mcap_path),
        "output_dir": str(resolved_output),
        "duration_seconds_requested": float(duration_seconds),
        "bin_width_ns": DEFAULT_BIN_WIDTH_NS,
        "span": span,
        "decoded_summary": decoded.to_json_summary(),
        "selection": {
            "start_bin": selection.start_bin,
            "stop_bin_exclusive": selection.stop_bin_exclusive,
            "length_bins": len(window_bins),
            "reason": selection.reason,
            "score": selection.score,
            "start_ns": window_bins[0].start_ns,
            "end_ns": window_bins[-1].end_ns,
            "relative_start_seconds_from_span_start": (window_bins[0].start_ns - span["start_ns"]) / 1_000_000_000,
            "relative_end_seconds_from_span_start": (window_bins[-1].end_ns - span["start_ns"]) / 1_000_000_000,
        },
        "tokenizer": {
            "tokens_per_bin": resolved_tokenizer.tokens_per_bin,
            "slots_per_bin": resolved_tokenizer.slots_per_bin,
            "token_count": len(tokenized.tokens),
            "overflow_bin_count": tokenized.overflow_bin_count,
            "overflow_bin_fraction": tokenized.overflow_bin_fraction,
        },
        "keyboard_replay": replay["summary"],
        "artifacts": {
            "bins_jsonl": str(bins_path),
            "frame_count": len(frame_records),
            "frames_dir": str(resolved_output / "frames") if write_frames else None,
        },
    }
    write_json_artifact(summary, resolved_output / "summary.json", dataset_root=dataset_root)
    return summary


def bins_for_screen_span(decoded: DecodedMcapJsonActions) -> tuple[tuple[ActionBin, ...], dict[str, Any]]:
    """Return bins aligned to the decoded screen span, with timeline fallback."""

    screen_times = decoded.screen_media_pts_ns or decoded.screen_message_timestamps_ns
    if screen_times:
        start_ns = min(screen_times)
        stop_ns = max(screen_times) + 1
        policy = "screen_media_pts_ns" if decoded.screen_media_pts_ns else "screen_message_timestamps_ns"
    else:
        start_ns, stop_ns = decoded.timeline_span_ns(include_screen=True)
        policy = "decoded_input_timeline_fallback"
    binned = bin_decoded_mcap_json_actions(decoded, start_ns=start_ns, stop_ns=stop_ns, include_screen_span=True)
    span = {
        "policy": policy,
        "start_ns": start_ns,
        "stop_ns": stop_ns,
        "bin_count": len(binned.bins),
        "dropped_event_count": binned.dropped_event_count,
    }
    return binned.bins, span


def resolve_window_selection(
    bins: Sequence[ActionBin],
    *,
    length_bins: int,
    start_bin: int | None = None,
    start_seconds: float | None = None,
) -> TemporalWindowSelection:
    """Resolve a deterministic 10s-like window, preferring keyboard activity."""

    if length_bins <= 0:
        raise ValueError("length_bins must be positive")
    if not bins:
        raise ValueError("cannot select a window from no bins")
    if start_bin is not None and start_seconds is not None:
        raise ValueError("provide at most one of start_bin or start_seconds")

    max_start = max(0, len(bins) - length_bins)
    if start_seconds is not None:
        offset_bins = int(round(float(start_seconds) * 1_000_000_000 / DEFAULT_BIN_WIDTH_NS))
        start = min(max(0, offset_bins), max_start)
        return TemporalWindowSelection(start, min(length_bins, len(bins) - start), "explicit_start_seconds", 0.0)
    if start_bin is not None:
        start = min(max(0, int(start_bin)), max_start)
        return TemporalWindowSelection(start, min(length_bins, len(bins) - start), "explicit_start_bin", 0.0)

    scores = [_bin_activity_score(action_bin) for action_bin in bins]
    current = sum(scores[:length_bins])
    best_score = current
    best_start = 0
    for index in range(1, max_start + 1):
        current += scores[index + length_bins - 1] - scores[index - 1]
        if current > best_score:
            best_score = current
            best_start = index
    return TemporalWindowSelection(best_start, min(length_bins, len(bins) - best_start), "auto_max_keyboard_activity", best_score)


def replay_keyboard_state(
    bins: Sequence[ActionBin],
    window_start: int,
    window_stop_exclusive: int,
) -> dict[str, Any]:
    """Replay keyboard transitions and annotate window-bin before/after state."""

    active: set[str] = set()
    open_window_transition_by_key: dict[str, dict[str, Any]] = {}
    transitions_started_in_window: list[dict[str, Any]] = []
    active_at_window_start: set[str] = set()
    active_at_window_end: set[str] = set()
    bin_states: dict[str, dict[str, Any]] = {}
    duplicate_downs: list[dict[str, Any]] = []
    unmatched_ups: list[dict[str, Any]] = []

    for position, action_bin in enumerate(bins):
        in_window = window_start <= position < window_stop_exclusive
        if position == window_start:
            active_at_window_start = set(active)
        before = sorted(active)
        events = sorted(action_bin.keyboard_events, key=event_sort_key)
        for event in events:
            record = {
                "key": event.key,
                "timestamp_ns": event.timestamp_ns,
                "bin_index": action_bin.index,
                "event_type": event.event_type.value,
                "position": _event_position(position, window_start, window_stop_exclusive),
            }
            if event.event_type is KeyboardEventType.DOWN:
                if event.key in active:
                    duplicate_downs.append(record)
                    continue
                active.add(event.key)
                if in_window:
                    transition = {
                        "key": event.key,
                        "down_timestamp_ns": event.timestamp_ns,
                        "down_bin_index": action_bin.index,
                        "release_status": "unreleased_by_recording_end",
                        "up_timestamp_ns": None,
                        "up_bin_index": None,
                    }
                    transitions_started_in_window.append(transition)
                    open_window_transition_by_key[event.key] = transition
            elif event.event_type is KeyboardEventType.UP:
                if event.key not in active:
                    unmatched_ups.append(record)
                    continue
                active.remove(event.key)
                transition = open_window_transition_by_key.pop(event.key, None)
                if transition is not None:
                    transition["up_timestamp_ns"] = event.timestamp_ns
                    transition["up_bin_index"] = action_bin.index
                    transition["release_status"] = "released_within_window" if in_window else "released_after_window"
            else:  # pragma: no cover - enum is closed in Phase 0.
                raise ValueError(f"unsupported keyboard event type: {event.event_type}")
        after = sorted(active)
        if in_window:
            bin_states[str(action_bin.index)] = {
                "active_keys_before": before,
                "active_keys_after": after,
                "keyboard_events": [keyboard_event_json(event, action_bin.start_ns) for event in events],
            }
        if position + 1 == window_stop_exclusive:
            active_at_window_end = set(active)

    status_counts: dict[str, int] = {}
    for transition in transitions_started_in_window:
        status = str(transition["release_status"])
        status_counts[status] = status_counts.get(status, 0) + 1

    summary = {
        "active_keys_at_window_start": sorted(active_at_window_start),
        "active_keys_at_window_end": sorted(active_at_window_end),
        "active_keys_at_recording_end": sorted(active),
        "fresh_key_downs_started_in_window": len(transitions_started_in_window),
        "fresh_key_down_release_status_counts": status_counts,
        "all_fresh_key_downs_started_in_window_released_by_recording_end": all(
            transition["release_status"] != "unreleased_by_recording_end" for transition in transitions_started_in_window
        ),
        "duplicate_down_count_total": len(duplicate_downs),
        "duplicate_down_count_in_window": sum(item["position"] == "inside_window" for item in duplicate_downs),
        "unmatched_up_count_total": len(unmatched_ups),
        "unmatched_up_count_in_window": sum(item["position"] == "inside_window" for item in unmatched_ups),
        "transitions_started_in_window": transitions_started_in_window,
        "duplicate_down_examples": duplicate_downs[:20],
        "unmatched_up_examples": unmatched_ups[:20],
    }
    return {"summary": summary, "bin_states": bin_states}


def temporal_bin_record(
    action_bin: ActionBin,
    tokenized_bin: TokenizedActionBin,
    *,
    key_state: dict[str, Any],
    frame: dict[str, Any] | None,
) -> dict[str, Any]:
    """Serialize one 50ms bin for JSONL inspection."""

    return {
        "schema": "fdm_1_with_d2e.temporal_sanity_bin.v1",
        "bin_index": action_bin.index,
        "start_ns": action_bin.start_ns,
        "end_ns": action_bin.end_ns,
        "duration_ns": action_bin.duration_ns,
        "frame": frame,
        "action": {
            "mouse_dx": action_bin.mouse_dx,
            "mouse_dy": action_bin.mouse_dy,
            "sparse_event_count": action_bin.sparse_event_count,
            "sequence": action_sequence_json(action_bin),
            "keyboard_events": [keyboard_event_json(event, action_bin.start_ns) for event in action_bin.keyboard_events],
            "mouse_button_events": [mouse_button_event_json(event, action_bin.start_ns) for event in action_bin.mouse_button_events],
            "scroll_events": [scroll_event_json(event, action_bin.start_ns) for event in action_bin.scroll_events],
        },
        "tokenized_action": tokenized_bin_json(tokenized_bin),
        "metadata": {
            "active_keys_before": key_state["active_keys_before"],
            "active_keys_after": key_state["active_keys_after"],
        },
    }


def action_sequence_json(action_bin: ActionBin) -> list[dict[str, Any]]:
    """Return sorted action sequence entries, including aggregate mouse first."""

    sequence = [
        {
            "family": "mouse_move_aggregate",
            "timestamp_ns": action_bin.start_ns,
            "offset_ms": 0.0,
            "dx": action_bin.mouse_dx,
            "dy": action_bin.mouse_dy,
        }
    ]
    for event in action_bin.discrete_events:
        if isinstance(event, KeyboardEvent):
            sequence.append(keyboard_event_json(event, action_bin.start_ns))
        elif isinstance(event, MouseButtonEvent):
            sequence.append(mouse_button_event_json(event, action_bin.start_ns))
        elif isinstance(event, ScrollEvent):
            sequence.append(scroll_event_json(event, action_bin.start_ns))
    return sequence


def tokenized_bin_json(tokenized_bin: TokenizedActionBin) -> dict[str, Any]:
    return {
        "tokens": list(tokenized_bin.tokens),
        "mouse_token": tokenized_bin.mouse_token,
        "event_slots": [
            {
                "index": slot.index,
                "token": slot.token,
                "timestamp_ns": slot.timestamp_ns,
                "source_family": slot.source_family,
            }
            for slot in tokenized_bin.event_slots
        ],
        "original_mouse_dx": tokenized_bin.original_mouse_dx,
        "original_mouse_dy": tokenized_bin.original_mouse_dy,
        "overflow": None
        if tokenized_bin.overflow is None
        else {
            "original_event_count": tokenized_bin.overflow.original_event_count,
            "retained_event_count": tokenized_bin.overflow.retained_event_count,
            "dropped_event_count": tokenized_bin.overflow.dropped_event_count,
            "retained_tokens": list(tokenized_bin.overflow.retained_tokens),
            "dropped_tokens": list(tokenized_bin.overflow.dropped_tokens),
            "overflow_token": tokenized_bin.overflow.overflow_token,
        },
    }


def keyboard_event_json(event: KeyboardEvent, bin_start_ns: int) -> dict[str, Any]:
    return {
        "family": "keyboard",
        "timestamp_ns": event.timestamp_ns,
        "offset_ms": (event.timestamp_ns - bin_start_ns) / 1_000_000,
        "key": event.key,
        "event_type": event.event_type.value,
        "label": f"{event.key}:{event.event_type.value}",
    }


def mouse_button_event_json(event: MouseButtonEvent, bin_start_ns: int) -> dict[str, Any]:
    return {
        "family": "mouse_button",
        "timestamp_ns": event.timestamp_ns,
        "offset_ms": (event.timestamp_ns - bin_start_ns) / 1_000_000,
        "button": event.button.value,
        "event_type": event.event_type.value,
        "label": f"{event.button.value}:{event.event_type.value}",
    }


def scroll_event_json(event: ScrollEvent, bin_start_ns: int) -> dict[str, Any]:
    directions = [direction.value for direction in event.directions]
    return {
        "family": "scroll",
        "timestamp_ns": event.timestamp_ns,
        "offset_ms": (event.timestamp_ns - bin_start_ns) / 1_000_000,
        "delta_x": event.delta_x,
        "delta_y": event.delta_y,
        "directions": directions,
        "label": "scroll:" + ",".join(directions),
    }


def write_window_frames(
    *,
    video_path: Path,
    output_dir: Path,
    bins: Sequence[ActionBin],
    first_screen_ns: int,
    frame_overlay: bool = True,
) -> dict[int, dict[str, Any]]:
    """Write one PNG per bin with optional action-text overlay."""

    try:
        import cv2  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised on MLXP with --with opencv.
        raise RuntimeError("OpenCV is required for frame export; run with --with opencv-python-headless") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"could not open video: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 60.0)
    records: dict[int, dict[str, Any]] = {}
    try:
        for action_bin in bins:
            rel_ms = max(0.0, (action_bin.start_ns - first_screen_ns) / 1_000_000.0)
            cap.set(cv2.CAP_PROP_POS_MSEC, rel_ms)
            ok, frame = cap.read()
            fallback_frame_index = None
            if not ok or frame is None:
                fallback_frame_index = max(0, int(round((action_bin.start_ns - first_screen_ns) / 1_000_000_000.0 * fps)))
                cap.set(cv2.CAP_PROP_POS_FRAMES, fallback_frame_index)
                ok, frame = cap.read()
            if not ok or frame is None:
                records[action_bin.index] = {
                    "path": None,
                    "read_ok": False,
                    "relative_ms_from_first_screen": rel_ms,
                    "fallback_frame_index": fallback_frame_index,
                }
                continue
            if frame_overlay:
                frame = _draw_overlay(cv2, frame, action_bin, rel_ms)
            path = output_dir / f"bin_{action_bin.index:06d}.png"
            cv2.imwrite(str(path), frame)
            records[action_bin.index] = {
                "path": str(path),
                "read_ok": True,
                "relative_ms_from_first_screen": rel_ms,
                "fallback_frame_index": fallback_frame_index,
            }
    finally:
        cap.release()
    return records


def _draw_overlay(cv2: Any, frame: Any, action_bin: ActionBin, rel_ms: float) -> Any:
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (min(w, 1280), 210), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)
    lines = [
        f"bin={action_bin.index} rel_ms={rel_ms:.1f} width=50ms",
        f"mouse aggregate dx={action_bin.mouse_dx} dy={action_bin.mouse_dy} sparse_events={action_bin.sparse_event_count}",
        "keyboard=" + ", ".join(event["label"] for event in [keyboard_event_json(e, action_bin.start_ns) for e in action_bin.keyboard_events[:8]])
        if action_bin.keyboard_events else "keyboard=(none)",
        "buttons=" + ", ".join(event["label"] for event in [mouse_button_event_json(e, action_bin.start_ns) for e in action_bin.mouse_button_events[:8]])
        if action_bin.mouse_button_events else "buttons=(none)",
        "scroll=" + ", ".join(event["label"] for event in [scroll_event_json(e, action_bin.start_ns) for e in action_bin.scroll_events[:6]])
        if action_bin.scroll_events else "scroll=(none)",
    ]
    y = 28
    for line in lines:
        cv2.putText(frame, line[:150], (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        y += 32
    center = (w // 2, h // 2)
    scale = 2.0
    end = (
        int(max(0, min(w - 1, center[0] + action_bin.mouse_dx * scale))),
        int(max(0, min(h - 1, center[1] + action_bin.mouse_dy * scale))),
    )
    cv2.arrowedLine(frame, center, end, (0, 255, 255), 4, tipLength=0.18)
    cv2.circle(frame, center, 8, (0, 255, 255), -1)
    return frame


def _bin_activity_score(action_bin: ActionBin) -> float:
    movement = 1.0 if action_bin.mouse_dx or action_bin.mouse_dy else 0.0
    scroll_directions = sum(len(event.directions) for event in action_bin.scroll_events)
    return 5.0 * len(action_bin.keyboard_events) + 2.0 * len(action_bin.mouse_button_events) + scroll_directions + 0.01 * movement


def _event_position(position: int, window_start: int, window_stop_exclusive: int) -> str:
    if position < window_start:
        return "before_window"
    if position >= window_stop_exclusive:
        return "after_window"
    return "inside_window"


def availability_payload(*, config: str | None = None, config_exists: bool | None = None) -> dict[str, Any]:
    payload = {
        "schema": TEMPORAL_SANITY_SCHEMA,
        "story_id": TEMPORAL_SANITY_STORY_ID,
        "status": "temporal_sanity_exporter_available",
        "offline_only": True,
        "requires_mcap_for_real_export": True,
        "requires_video_for_frame_export": True,
        "default_duration_seconds": 10.0,
        "default_bin_width_ns": DEFAULT_BIN_WIDTH_NS,
    }
    if config is not None:
        payload["config"] = config
    if config_exists is not None:
        payload["config_exists"] = config_exists
    return payload


__all__ = [
    "TEMPORAL_SANITY_SCHEMA",
    "TEMPORAL_SANITY_STORY_ID",
    "TemporalWindowSelection",
    "action_sequence_json",
    "availability_payload",
    "bins_for_screen_span",
    "export_temporal_sanity_window",
    "replay_keyboard_state",
    "resolve_window_selection",
    "temporal_bin_record",
    "tokenized_bin_json",
]
