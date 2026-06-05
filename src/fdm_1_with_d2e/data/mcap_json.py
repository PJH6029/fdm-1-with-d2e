"""Decode JSON/JSONSchema D2E MCAP messages into canonical Phase 0 events.

The real D2E MCAP files observed in the Phase 0 G009 cluster scan use JSON
payloads on topics such as ``keyboard``, ``mouse/raw``, ``mouse``, and
``screen``.  This module keeps decoding dependency-light for offline tests:
callers may pass already-decoded synthetic records, while real ``.mcap`` reads
go through the optional adapter in :mod:`fdm_1_with_d2e.data.reader`.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from fdm_1_with_d2e.data.binning import bin_input_events, normalise_mouse_delta
from fdm_1_with_d2e.data.reader import OWAMcapReader
from fdm_1_with_d2e.data.types import (
    DEFAULT_BIN_WIDTH_NS,
    BinningResult,
    KeyboardEvent,
    KeyboardEventType,
    MouseButton,
    MouseButtonEvent,
    MouseButtonEventType,
    MouseMoveEvent,
    OWAMcapMessage,
    ScreenEvent,
    ScreenEventType,
    ScrollEvent,
    event_sort_key,
)

JSONDict = dict[str, Any]
RawMcapJsonRecord = OWAMcapMessage | Mapping[str, Any]

_IGNORED_TOPICS = frozenset({"keyboard/state", "mouse/state", "window"})
_KEYBOARD_EVENT_TYPES = {
    "press": KeyboardEventType.DOWN,
    "pressed": KeyboardEventType.DOWN,
    "down": KeyboardEventType.DOWN,
    "release": KeyboardEventType.UP,
    "released": KeyboardEventType.UP,
    "up": KeyboardEventType.UP,
}


@dataclass(frozen=True, slots=True)
class McapJsonDecodeIssue:
    """Small diagnostic for a malformed or unsupported JSON MCAP message."""

    topic: str
    timestamp_ns: int | None
    reason: str

    def to_json(self) -> JSONDict:
        return {
            "topic": self.topic,
            "timestamp_ns": self.timestamp_ns,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class DecodedMcapJsonActions:
    """Canonical events and bounded diagnostics decoded from one recording."""

    keyboard_events: tuple[KeyboardEvent, ...] = ()
    mouse_move_events: tuple[MouseMoveEvent, ...] = ()
    mouse_button_events: tuple[MouseButtonEvent, ...] = ()
    scroll_events: tuple[ScrollEvent, ...] = ()
    screen_events: tuple[ScreenEvent, ...] = ()
    screen_message_timestamps_ns: tuple[int, ...] = ()
    screen_media_pts_ns: tuple[int, ...] = ()
    topic_counts: Mapping[str, int] | None = None
    ignored_topic_counts: Mapping[str, int] | None = None
    ignored_absolute_mouse_move_count: int = 0
    issues: tuple[McapJsonDecodeIssue, ...] = ()

    @property
    def input_event_count(self) -> int:
        return (
            len(self.keyboard_events)
            + len(self.mouse_move_events)
            + len(self.mouse_button_events)
            + len(self.scroll_events)
        )

    @property
    def decoded_event_counts(self) -> dict[str, int]:
        return {
            "keyboard": len(self.keyboard_events),
            "mouse_move": len(self.mouse_move_events),
            "mouse_button": len(self.mouse_button_events),
            "scroll": len(self.scroll_events),
            "screen": len(self.screen_events),
        }

    def timeline_span_ns(self, *, include_screen: bool = True) -> tuple[int, int]:
        """Return a half-open-ish decode span suitable for 50ms bin creation."""

        timestamps = [
            *(event.timestamp_ns for event in self.keyboard_events),
            *(event.timestamp_ns for event in self.mouse_move_events),
            *(event.timestamp_ns for event in self.mouse_button_events),
            *(event.timestamp_ns for event in self.scroll_events),
        ]
        if include_screen:
            timestamps.extend(self.screen_message_timestamps_ns)
        if not timestamps:
            return (0, 0)
        return (min(timestamps), max(timestamps) + 1)

    def to_json_summary(self) -> JSONDict:
        """Return bounded decode diagnostics for run records and CLI output."""

        return {
            "topic_counts": _sorted_count_dict(self.topic_counts or {}),
            "ignored_topic_counts": _sorted_count_dict(self.ignored_topic_counts or {}),
            "decoded_event_counts": self.decoded_event_counts,
            "input_event_count": self.input_event_count,
            "ignored_absolute_mouse_move_count": self.ignored_absolute_mouse_move_count,
            "screen_frame_count": len(self.screen_message_timestamps_ns),
            "screen_message_time_range_ns": _range_json(self.screen_message_timestamps_ns),
            "screen_media_pts_range_ns": _range_json(self.screen_media_pts_ns),
            "input_time_range_ns": _range_json(
                [
                    *(event.timestamp_ns for event in self.keyboard_events),
                    *(event.timestamp_ns for event in self.mouse_move_events),
                    *(event.timestamp_ns for event in self.mouse_button_events),
                    *(event.timestamp_ns for event in self.scroll_events),
                ]
            ),
            "issue_count": len(self.issues),
            "issues": [issue.to_json() for issue in self.issues[:20]],
            "issues_truncated": len(self.issues) > 20,
        }


def read_d2e_json_mcap_actions(mcap_path: str | Path) -> DecodedMcapJsonActions:
    """Read one JSON-encoded D2E MCAP file through the optional MCAP adapter."""

    return decode_d2e_json_mcap_records(OWAMcapReader(mcap_path).iter_raw_messages())


def decode_d2e_json_mcap_records(records: Iterable[RawMcapJsonRecord]) -> DecodedMcapJsonActions:
    """Decode raw MCAP-like JSON records into canonical event dataclasses.

    ``records`` may contain :class:`OWAMcapMessage` objects from the optional
    reader, or dependency-free fixture dictionaries with ``topic``, a timestamp
    field such as ``log_time_ns``, and ``data``/``payload`` as either a mapping,
    JSON string, or JSON bytes.
    """

    topic_counts: Counter[str] = Counter()
    ignored_topic_counts: Counter[str] = Counter()
    keyboard_events: list[KeyboardEvent] = []
    mouse_move_events: list[MouseMoveEvent] = []
    mouse_button_events: list[MouseButtonEvent] = []
    scroll_events: list[ScrollEvent] = []
    screen_events: list[ScreenEvent] = []
    screen_message_timestamps: list[int] = []
    screen_media_pts: list[int] = []
    issues: list[McapJsonDecodeIssue] = []
    ignored_absolute_mouse_move_count = 0

    for record in records:
        topic = _record_topic(record)
        topic_counts[topic] += 1
        payload, payload_error = _record_payload(record)
        try:
            timestamp_ns = _record_timestamp_ns(record, payload)
        except (TypeError, ValueError) as exc:
            issues.append(McapJsonDecodeIssue(topic=topic, timestamp_ns=None, reason=str(exc)))
            continue
        if payload_error is not None:
            issues.append(McapJsonDecodeIssue(topic=topic, timestamp_ns=timestamp_ns, reason=payload_error))
            continue
        if payload is None:  # pragma: no cover - kept for defensive typing.
            issues.append(McapJsonDecodeIssue(topic=topic, timestamp_ns=timestamp_ns, reason="missing JSON payload"))
            continue

        try:
            if topic == "keyboard":
                keyboard_events.append(_decode_keyboard_event(payload, timestamp_ns))
            elif topic == "mouse/raw":
                mouse_move_events.append(_decode_raw_mouse_event(payload, timestamp_ns))
            elif topic == "mouse":
                mouse_event = _decode_mouse_event(payload, timestamp_ns)
                if isinstance(mouse_event, MouseButtonEvent):
                    mouse_button_events.append(mouse_event)
                elif isinstance(mouse_event, ScrollEvent):
                    scroll_events.append(mouse_event)
                elif mouse_event == "absolute_move_ignored":
                    ignored_absolute_mouse_move_count += 1
                else:  # pragma: no cover - defensive for future return variants.
                    raise TypeError(f"unexpected decoded mouse event: {mouse_event!r}")
            elif topic == "screen":
                screen_event = _decode_screen_event(payload, timestamp_ns)
                screen_events.append(screen_event)
                screen_message_timestamps.append(screen_event.timestamp_ns)
                media_pts_ns = _screen_media_pts_ns(payload)
                if media_pts_ns is not None:
                    screen_media_pts.append(media_pts_ns)
            elif topic in _IGNORED_TOPICS:
                ignored_topic_counts[topic] += 1
            else:
                ignored_topic_counts[topic] += 1
        except (TypeError, ValueError) as exc:
            issues.append(McapJsonDecodeIssue(topic=topic, timestamp_ns=timestamp_ns, reason=str(exc)))

    return DecodedMcapJsonActions(
        keyboard_events=tuple(sorted(keyboard_events, key=event_sort_key)),
        mouse_move_events=tuple(sorted(mouse_move_events, key=event_sort_key)),
        mouse_button_events=tuple(sorted(mouse_button_events, key=event_sort_key)),
        scroll_events=tuple(sorted(scroll_events, key=event_sort_key)),
        screen_events=tuple(sorted(screen_events, key=event_sort_key)),
        screen_message_timestamps_ns=tuple(sorted(screen_message_timestamps)),
        screen_media_pts_ns=tuple(sorted(screen_media_pts)),
        topic_counts=dict(topic_counts),
        ignored_topic_counts=dict(ignored_topic_counts),
        ignored_absolute_mouse_move_count=ignored_absolute_mouse_move_count,
        issues=tuple(issues),
    )


def bin_decoded_mcap_json_actions(
    decoded: DecodedMcapJsonActions,
    *,
    start_ns: int | None = None,
    stop_ns: int | None = None,
    bin_width_ns: int = DEFAULT_BIN_WIDTH_NS,
    include_screen_span: bool = True,
) -> BinningResult:
    """Bin decoded canonical input events using the existing 50ms binning contract."""

    if start_ns is None or stop_ns is None:
        span_start_ns, span_stop_ns = decoded.timeline_span_ns(include_screen=include_screen_span)
        if start_ns is None:
            start_ns = span_start_ns
        if stop_ns is None:
            stop_ns = span_stop_ns
    return bin_input_events(
        start_ns=start_ns,
        stop_ns=stop_ns,
        keyboard_events=decoded.keyboard_events,
        mouse_button_events=decoded.mouse_button_events,
        scroll_events=decoded.scroll_events,
        mouse_move_events=decoded.mouse_move_events,
        bin_width_ns=bin_width_ns,
    )


def _decode_keyboard_event(payload: Mapping[str, Any], timestamp_ns: int) -> KeyboardEvent:
    raw_event_type = _string_field(payload, "event_type", "type", "kind").casefold()
    try:
        event_type = _KEYBOARD_EVENT_TYPES[raw_event_type]
    except KeyError as exc:
        raise ValueError(f"unsupported keyboard event_type: {raw_event_type!r}") from exc
    return KeyboardEvent(timestamp_ns=timestamp_ns, key=_keyboard_key_label(payload), event_type=event_type)


def _decode_raw_mouse_event(payload: Mapping[str, Any], timestamp_ns: int) -> MouseMoveEvent:
    dx, dy, source_fields = normalise_mouse_delta(payload)
    return MouseMoveEvent(timestamp_ns=timestamp_ns, dx=dx, dy=dy, source_fields=source_fields)


def _decode_mouse_event(
    payload: Mapping[str, Any],
    timestamp_ns: int,
) -> MouseButtonEvent | ScrollEvent | str:
    event_type = _string_field(payload, "event_type", "type", "kind", default="").casefold()
    if event_type == "click" or ("button" in payload and "pressed" in payload):
        button = _mouse_button(payload.get("button"))
        pressed = _bool_field(payload, "pressed")
        transition = MouseButtonEventType.DOWN if pressed else MouseButtonEventType.UP
        return MouseButtonEvent(timestamp_ns=timestamp_ns, button=button, event_type=transition)
    if event_type == "scroll" or ("dx" in payload and "dy" in payload and event_type != "move"):
        return ScrollEvent(
            timestamp_ns=timestamp_ns,
            delta_x=_int_field(payload, "dx", default=0),
            delta_y=_int_field(payload, "dy", default=0),
        )
    if event_type == "move" or ("x" in payload and "y" in payload):
        return "absolute_move_ignored"
    raise ValueError(f"unsupported mouse event_type: {event_type!r}")


def _decode_screen_event(payload: Mapping[str, Any], timestamp_ns: int) -> ScreenEvent:
    value: JSONDict = {}
    if "shape" in payload:
        value["shape"] = payload["shape"]
    if "source_shape" in payload:
        value["source_shape"] = payload["source_shape"]
    media_pts_ns = _screen_media_pts_ns(payload)
    if media_pts_ns is not None:
        value["media_pts_ns"] = media_pts_ns
    return ScreenEvent(timestamp_ns=timestamp_ns, event_type=ScreenEventType.SCREEN_SIZE, value=value)


def _record_topic(record: RawMcapJsonRecord) -> str:
    if isinstance(record, OWAMcapMessage):
        return record.topic
    return str(record.get("topic", ""))


def _record_payload(record: RawMcapJsonRecord) -> tuple[Mapping[str, Any] | None, str | None]:
    raw_payload: object
    if isinstance(record, OWAMcapMessage):
        raw_payload = record.data
    else:
        raw_payload = record.get("payload", record.get("data", record.get("json")))

    if isinstance(raw_payload, Mapping):
        return raw_payload, None
    if isinstance(raw_payload, bytes):
        try:
            raw_payload = raw_payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            return None, f"payload is not UTF-8 JSON bytes: {exc}"
    if isinstance(raw_payload, str):
        try:
            decoded = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            return None, f"payload is not valid JSON: {exc}"
        if isinstance(decoded, Mapping):
            return decoded, None
        return None, f"JSON payload must be an object, got {type(decoded).__name__}"
    return None, f"payload must be a JSON object/string/bytes, got {type(raw_payload).__name__}"


def _record_timestamp_ns(record: RawMcapJsonRecord, payload: Mapping[str, Any] | None) -> int:
    if isinstance(record, OWAMcapMessage):
        return int(record.log_time_ns)
    for key in ("log_time_ns", "log_time", "timestamp_ns", "time_ns", "publish_time_ns", "publish_time"):
        if key in record and record[key] is not None:
            return int(record[key])
    if payload is not None:
        for key in ("timestamp_ns", "time_ns", "ts_ns"):
            if key in payload and payload[key] is not None:
                return int(payload[key])
    raise ValueError("record must contain a nanosecond timestamp field such as log_time_ns")


def _keyboard_key_label(payload: Mapping[str, Any]) -> str:
    for key in ("key", "key_name", "name"):
        if key in payload and payload[key] is not None:
            value = str(payload[key]).strip()
            if value:
                return value.replace(" ", "_")
    for key in ("vk", "virtual_key", "virtual_key_code"):
        if key in payload and payload[key] is not None:
            return f"VK_{int(payload[key])}"
    raise ValueError("keyboard event missing key/vk field")


def _mouse_button(value: object) -> MouseButton:
    if value is None:
        raise ValueError("mouse click event missing button field")
    label = str(value).strip().casefold().split(".")[-1]
    try:
        return MouseButton(label)
    except ValueError as exc:
        raise ValueError(f"unsupported mouse button: {value!r}") from exc


def _screen_media_pts_ns(payload: Mapping[str, Any]) -> int | None:
    media_ref = payload.get("media_ref")
    if isinstance(media_ref, Mapping):
        for key in ("pts_ns", "timestamp_ns", "time_ns"):
            if key in media_ref and media_ref[key] is not None:
                return int(media_ref[key])
    return None


def _string_field(
    payload: Mapping[str, Any],
    *keys: str,
    default: str | None = None,
) -> str:
    for key in keys:
        if key in payload and payload[key] is not None:
            return str(payload[key])
    if default is not None:
        return default
    raise ValueError(f"payload missing required string field from {keys}")


def _int_field(payload: Mapping[str, Any], key: str, *, default: int | None = None) -> int:
    if key not in payload or payload[key] is None:
        if default is not None:
            return default
        raise ValueError(f"payload missing required integer field {key!r}")
    return int(payload[key])


def _bool_field(payload: Mapping[str, Any], key: str) -> bool:
    value = payload.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "1", "yes", "y", "down", "pressed"}:
            return True
        if normalized in {"false", "0", "no", "n", "up", "released"}:
            return False
    raise ValueError(f"payload field {key!r} must be boolean-like")


def _range_json(values: Iterable[int]) -> JSONDict | None:
    items = tuple(int(value) for value in values)
    if not items:
        return None
    return {
        "start_ns": min(items),
        "end_ns": max(items),
        "count": len(items),
    }


def _sorted_count_dict(counts: Mapping[str, int]) -> dict[str, int]:
    return {key: int(counts[key]) for key in sorted(counts, key=str.casefold)}


__all__ = [
    "DecodedMcapJsonActions",
    "McapJsonDecodeIssue",
    "RawMcapJsonRecord",
    "bin_decoded_mcap_json_actions",
    "decode_d2e_json_mcap_records",
    "read_d2e_json_mcap_actions",
]
