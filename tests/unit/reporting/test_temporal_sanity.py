from __future__ import annotations

from fdm_1_with_d2e.data import ActionBin, KeyboardEvent, KeyboardEventType, MouseButton, MouseButtonEvent, MouseButtonEventType, ns_from_ms
from fdm_1_with_d2e.reporting.temporal_sanity import replay_keyboard_state, resolve_window_selection, temporal_bin_record
from fdm_1_with_d2e.tokenization import ActionTokenizer


def test_auto_window_selection_prefers_keyboard_activity() -> None:
    bins = tuple(
        ActionBin(
            index=index,
            start_ns=ns_from_ms(index * 50),
            end_ns=ns_from_ms((index + 1) * 50),
            keyboard_events=(
                KeyboardEvent(ns_from_ms(index * 50 + 1), f"K{index}", KeyboardEventType.DOWN),
            )
            if index in {3, 4}
            else (),
        )
        for index in range(8)
    )

    selection = resolve_window_selection(bins, length_bins=2)

    assert selection.start_bin == 3
    assert selection.stop_bin_exclusive == 5
    assert selection.reason == "auto_max_keyboard_activity"


def test_keyboard_replay_reports_release_status_and_duplicate_downs() -> None:
    bins = (
        ActionBin(0, ns_from_ms(0), ns_from_ms(50), keyboard_events=(KeyboardEvent(ns_from_ms(1), "PRE", KeyboardEventType.DOWN),)),
        ActionBin(1, ns_from_ms(50), ns_from_ms(100), keyboard_events=(KeyboardEvent(ns_from_ms(55), "A", KeyboardEventType.DOWN),)),
        ActionBin(
            2,
            ns_from_ms(100),
            ns_from_ms(150),
            keyboard_events=(
                KeyboardEvent(ns_from_ms(105), "A", KeyboardEventType.DOWN),
                KeyboardEvent(ns_from_ms(110), "B", KeyboardEventType.DOWN),
                KeyboardEvent(ns_from_ms(120), "B", KeyboardEventType.UP),
            ),
        ),
        ActionBin(3, ns_from_ms(150), ns_from_ms(200), keyboard_events=(KeyboardEvent(ns_from_ms(160), "A", KeyboardEventType.UP),)),
        ActionBin(4, ns_from_ms(200), ns_from_ms(250), keyboard_events=(KeyboardEvent(ns_from_ms(210), "PRE", KeyboardEventType.UP),)),
    )

    replay = replay_keyboard_state(bins, 1, 3)
    summary = replay["summary"]

    assert summary["active_keys_at_window_start"] == ["PRE"]
    assert summary["active_keys_at_window_end"] == ["A", "PRE"]
    assert summary["fresh_key_downs_started_in_window"] == 2
    assert summary["fresh_key_down_release_status_counts"] == {
        "released_after_window": 1,
        "released_within_window": 1,
    }
    assert summary["all_fresh_key_downs_started_in_window_released_by_recording_end"] is True
    assert summary["duplicate_down_count_in_window"] == 1
    assert replay["bin_states"]["1"]["active_keys_before"] == ["PRE"]
    assert replay["bin_states"]["2"]["active_keys_after"] == ["A", "PRE"]


def test_temporal_bin_record_contains_action_tokens_and_key_state() -> None:
    action_bin = ActionBin(
        7,
        ns_from_ms(350),
        ns_from_ms(400),
        mouse_dx=3,
        mouse_dy=-4,
        keyboard_events=(KeyboardEvent(ns_from_ms(360), "VK_65", KeyboardEventType.DOWN),),
        mouse_button_events=(MouseButtonEvent(ns_from_ms(365), MouseButton.LEFT, MouseButtonEventType.DOWN),),
    )
    tokenized = ActionTokenizer().tokenize_bin(action_bin)

    record = temporal_bin_record(
        action_bin,
        tokenized,
        key_state={"active_keys_before": [], "active_keys_after": ["VK_65"]},
        frame={"path": "frames/bin_000007.png", "read_ok": True},
    )

    assert record["frame"]["path"].endswith("bin_000007.png")
    assert record["action"]["mouse_dx"] == 3
    assert record["tokenized_action"]["tokens"][1:3] == ["KEY_DOWN_VK_65", "MOUSE_LEFT_DOWN"]
    assert record["metadata"]["active_keys_after"] == ["VK_65"]
