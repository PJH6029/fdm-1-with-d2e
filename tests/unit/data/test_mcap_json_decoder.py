from __future__ import annotations

import json

from fdm_1_with_d2e.data import (
    KeyboardEventType,
    MouseButton,
    MouseButtonEventType,
    ScreenEventType,
    bin_decoded_mcap_json_actions,
    decode_d2e_json_mcap_records,
    ns_from_ms,
)


def _record(topic: str, timestamp_ms: int, payload: dict[str, object]) -> dict[str, object]:
    return {
        "topic": topic,
        "log_time_ns": ns_from_ms(timestamp_ms),
        "data": json.dumps(payload).encode("utf-8"),
    }


def test_decode_json_mcap_records_maps_real_d2e_topic_shapes_to_canonical_events() -> None:
    decoded = decode_d2e_json_mcap_records(
        [
            _record("screen", 0, {"media_ref": {"pts_ns": 0}, "shape": [480, 854, 3]}),
            _record("keyboard", 10, {"event_type": "press", "vk": 87}),
            _record("mouse/raw", 20, {"last_x": 4, "last_y": -3}),
            _record("mouse", 30, {"event_type": "move", "x": 100, "y": 200}),
            _record("keyboard", 40, {"event_type": "release", "vk": 87}),
            _record("mouse/raw", 60, {"dx": -2, "dy": 1}),
            _record("mouse", 70, {"event_type": "click", "button": "left", "pressed": True}),
            _record("mouse", 90, {"event_type": "click", "button": "left", "pressed": False}),
            _record("mouse", 100, {"event_type": "scroll", "dx": 1, "dy": -2}),
            _record(
                "screen",
                120,
                {"media_ref": {"pts_ns": ns_from_ms(120)}, "shape": [480, 854, 3], "source_shape": [720, 1280, 3]},
            ),
            _record("keyboard/state", 125, {"pressed": [87]}),
        ]
    )

    assert [event.event_type for event in decoded.keyboard_events] == [
        KeyboardEventType.DOWN,
        KeyboardEventType.UP,
    ]
    assert [event.key for event in decoded.keyboard_events] == ["VK_87", "VK_87"]
    assert [(event.dx, event.dy, event.source_fields) for event in decoded.mouse_move_events] == [
        (4, -3, ("last_x", "last_y")),
        (-2, 1, ("dx", "dy")),
    ]
    assert [(event.button, event.event_type) for event in decoded.mouse_button_events] == [
        (MouseButton.LEFT, MouseButtonEventType.DOWN),
        (MouseButton.LEFT, MouseButtonEventType.UP),
    ]
    assert [(event.delta_x, event.delta_y) for event in decoded.scroll_events] == [(1, -2)]
    assert [event.event_type for event in decoded.screen_events] == [
        ScreenEventType.SCREEN_SIZE,
        ScreenEventType.SCREEN_SIZE,
    ]
    assert decoded.ignored_absolute_mouse_move_count == 1
    assert decoded.ignored_topic_counts == {"keyboard/state": 1}
    assert decoded.issues == ()

    summary = decoded.to_json_summary()
    assert summary["decoded_event_counts"] == {
        "keyboard": 2,
        "mouse_move": 2,
        "mouse_button": 2,
        "scroll": 1,
        "screen": 2,
    }
    assert summary["screen_frame_count"] == 2
    assert summary["screen_message_time_range_ns"] == {
        "start_ns": 0,
        "end_ns": ns_from_ms(120),
        "count": 2,
    }
    assert summary["screen_media_pts_range_ns"] == {
        "start_ns": 0,
        "end_ns": ns_from_ms(120),
        "count": 2,
    }


def test_bin_decoded_json_mcap_actions_uses_raw_mouse_not_absolute_move() -> None:
    decoded = decode_d2e_json_mcap_records(
        [
            _record("screen", 0, {"media_ref": {"pts_ns": 0}, "shape": [480, 854, 3]}),
            _record("mouse/raw", 10, {"last_x": 5, "last_y": 6}),
            _record("mouse", 20, {"event_type": "move", "x": 999, "y": 888}),
            _record("mouse/raw", 60, {"last_x": -2, "last_y": 3}),
            _record("mouse", 75, {"event_type": "scroll", "dx": 0, "dy": 1}),
            _record("screen", 100, {"media_ref": {"pts_ns": ns_from_ms(100)}, "shape": [480, 854, 3]}),
        ]
    )

    binned = bin_decoded_mcap_json_actions(decoded)

    assert [(action_bin.mouse_dx, action_bin.mouse_dy, action_bin.sparse_event_count) for action_bin in binned.bins] == [
        (5, 6, 0),
        (-2, 3, 1),
        (0, 0, 0),
    ]
    assert binned.dropped_event_count == 0
    assert decoded.ignored_absolute_mouse_move_count == 1


def test_decode_json_mcap_records_reports_malformed_messages_without_mcap_dependency() -> None:
    decoded = decode_d2e_json_mcap_records(
        [
            {"topic": "keyboard", "log_time_ns": 1, "data": b"not-json"},
            {"topic": "mouse/raw", "data": {"last_x": 1, "last_y": 2}},
            _record("mouse", 5, {"event_type": "click", "button": "side", "pressed": True}),
        ]
    )

    assert decoded.input_event_count == 0
    assert [issue.topic for issue in decoded.issues] == ["keyboard", "mouse/raw", "mouse"]
    assert "not valid JSON" in decoded.issues[0].reason
    assert "timestamp" in decoded.issues[1].reason
    assert "unsupported mouse button" in decoded.issues[2].reason
