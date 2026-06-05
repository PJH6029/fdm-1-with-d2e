from __future__ import annotations

from fdm_1_with_d2e.data import (
    KeyboardEvent,
    KeyboardEventType,
    MouseButton,
    MouseButtonEvent,
    MouseButtonEventType,
    ScrollEvent,
    bin_input_events,
    ns_from_ms,
)
from fdm_1_with_d2e.evaluation.roundtrip import (
    tokenized_bins_to_canonical_events,
    tokenized_bins_to_writer_records,
)
from fdm_1_with_d2e.tokenization import ActionTokenizer, NO_ACTION


def test_binned_actions_round_trip_to_writer_compatible_records() -> None:
    binned = bin_input_events(
        start_ns=0,
        stop_ns=ns_from_ms(100),
        keyboard_events=[
            KeyboardEvent(ns_from_ms(10), "SPACE", KeyboardEventType.DOWN),
            KeyboardEvent(ns_from_ms(60), "SPACE", KeyboardEventType.UP),
        ],
        mouse_button_events=[
            MouseButtonEvent(ns_from_ms(20), MouseButton.LEFT, MouseButtonEventType.DOWN),
        ],
        scroll_events=[ScrollEvent(ns_from_ms(70), delta_x=1)],
        mouse_move_events=[
            {"timestamp_ns": ns_from_ms(5), "dx": 3, "dy": -2},
            {"timestamp_ns": ns_from_ms(55), "last_x": -4, "last_y": 6},
        ],
    )
    tokenizer = ActionTokenizer()
    tokenized = tokenizer.tokenize_bins(binned.bins)

    events = tokenized_bins_to_canonical_events(tokenized, tokenizer=tokenizer)
    records = tokenized_bins_to_writer_records(tokenized, tokenizer=tokenizer)

    assert tokenized.overflow_records == ()
    assert [record["topic"] for record in records] == [
        "mouse_move",
        "keyboard",
        "mouse_button",
        "mouse_move",
        "keyboard",
        "scroll",
    ]
    assert records[0]["dx"] == records[0]["last_x"]
    assert records[0]["dy"] == records[0]["last_y"]
    assert records[1] == {
        "timestamp_ns": ns_from_ms(10),
        "family": "keyboard",
        "topic": "keyboard",
        "key": "SPACE",
        "event_type": "down",
    }
    assert records[2]["button"] == "left"
    assert records[-1]["directions"] == ("right",)
    assert [event.timestamp_ns for event in events] == sorted(event.timestamp_ns for event in events)


def test_raw_prediction_tokens_convert_to_events_without_noop_or_padding_records() -> None:
    tokenizer = ActionTokenizer()
    first = (
        "MOUSE_MOVE_BIN_25_24",
        "KEY_DOWN_A",
        *(NO_ACTION for _ in range(7)),
    )
    second = (
        "MOUSE_MOVE_BIN_24_24",
        "KEY_UP_A",
        "MOUSE_LEFT_UP",
        *(NO_ACTION for _ in range(6)),
    )

    records = tokenized_bins_to_writer_records(
        (first, second),
        tokenizer=tokenizer,
        start_ns=ns_from_ms(500),
    )

    assert [record["topic"] for record in records] == [
        "mouse_move",
        "keyboard",
        "keyboard",
        "mouse_button",
    ]
    assert records[0]["timestamp_ns"] == ns_from_ms(500)
    assert records[0]["dx"] > 0
    assert records[0]["dy"] == 0
    assert records[1]["timestamp_ns"] < records[2]["timestamp_ns"] < records[3]["timestamp_ns"]
    assert all(record["family"] != "special" for record in records)
