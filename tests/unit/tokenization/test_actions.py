from __future__ import annotations

import pytest

from fdm_1_with_d2e.data import (
    ActionBin,
    KeyboardEvent,
    KeyboardEventType,
    MouseButton,
    MouseButtonEvent,
    MouseButtonEventType,
    ScrollDirection,
    ScrollEvent,
    ns_from_ms,
)
from fdm_1_with_d2e.tokenization import (
    EVENT_OVERFLOW,
    NO_ACTION,
    PAD_ACTION,
    ActionTokenizer,
    MouseQuantizer,
)


def test_tokenize_bin_uses_fixed_mouse_plus_k_slots_and_timestamp_order() -> None:
    axis = MouseQuantizer.default().x_axis
    dx = axis.positive_representative(2)
    dy = -axis.positive_representative(1)
    action_bin = ActionBin(
        index=0,
        start_ns=0,
        end_ns=ns_from_ms(50),
        mouse_dx=dx,
        mouse_dy=dy,
        keyboard_events=(
            KeyboardEvent(timestamp_ns=ns_from_ms(20), key="SPACE", event_type=KeyboardEventType.DOWN),
        ),
        mouse_button_events=(
            MouseButtonEvent(
                timestamp_ns=ns_from_ms(10),
                button=MouseButton.LEFT,
                event_type=MouseButtonEventType.DOWN,
            ),
        ),
        scroll_events=(ScrollEvent(timestamp_ns=ns_from_ms(30), delta_y=1),),
    )
    tokenizer = ActionTokenizer()

    tokenized = tokenizer.tokenize_bin(action_bin)

    assert len(tokenized.tokens) == 9
    assert tokenized.tokens[:4] == (
        "MOUSE_MOVE_BIN_27_22",
        "MOUSE_LEFT_DOWN",
        "KEY_DOWN_SPACE",
        "SCROLL_UP",
    )
    assert tokenized.tokens[4:] == (NO_ACTION, NO_ACTION, NO_ACTION, NO_ACTION, NO_ACTION)
    assert tokenized.overflow is None

    reconstructed = tokenizer.detokenize_bin(tokenized)
    assert (reconstructed.mouse_dx, reconstructed.mouse_dy) == (dx, dy)
    assert [(event.family.value, event.timestamp_ns) for event in reconstructed.discrete_events] == [
        ("mouse_button", ns_from_ms(10)),
        ("keyboard", ns_from_ms(20)),
        ("scroll", ns_from_ms(30)),
    ]
    assert reconstructed.keyboard_events[0].key == "SPACE"
    assert reconstructed.mouse_button_events[0].button is MouseButton.LEFT
    assert reconstructed.scroll_events[0].directions == (ScrollDirection.UP,)


def test_overflow_reserves_marker_and_preserves_buttons_then_key_downs() -> None:
    action_bin = ActionBin(
        index=3,
        start_ns=ns_from_ms(150),
        end_ns=ns_from_ms(200),
        mouse_button_events=(
            MouseButtonEvent(ns_from_ms(151), MouseButton.LEFT, MouseButtonEventType.DOWN),
            MouseButtonEvent(ns_from_ms(152), MouseButton.RIGHT, MouseButtonEventType.UP),
        ),
        keyboard_events=(
            KeyboardEvent(ns_from_ms(153), "A", KeyboardEventType.DOWN),
            KeyboardEvent(ns_from_ms(154), "B", KeyboardEventType.DOWN),
            KeyboardEvent(ns_from_ms(155), "C", KeyboardEventType.DOWN),
            KeyboardEvent(ns_from_ms(156), "D", KeyboardEventType.DOWN),
            KeyboardEvent(ns_from_ms(157), "E", KeyboardEventType.DOWN),
            KeyboardEvent(ns_from_ms(158), "A", KeyboardEventType.UP),
            KeyboardEvent(ns_from_ms(159), "B", KeyboardEventType.UP),
        ),
        scroll_events=(ScrollEvent(ns_from_ms(160), delta_y=-1),),
    )
    tokenizer = ActionTokenizer()

    tokenized = tokenizer.tokenize_bin(action_bin)

    assert tokenized.event_tokens == (
        "MOUSE_LEFT_DOWN",
        "MOUSE_RIGHT_UP",
        "KEY_DOWN_A",
        "KEY_DOWN_B",
        "KEY_DOWN_C",
        "KEY_DOWN_D",
        "KEY_DOWN_E",
        EVENT_OVERFLOW,
    )
    assert tokenized.overflow is not None
    assert tokenized.overflow.original_event_count == 10
    assert tokenized.overflow.retained_event_count == 7
    assert tokenized.overflow.dropped_event_count == 3
    assert tokenized.overflow.dropped_tokens == ("KEY_UP_A", "KEY_UP_B", "SCROLL_DOWN")

    reconstructed = tokenizer.detokenize_bin(tokenized)
    assert [event.key for event in reconstructed.keyboard_events] == ["A", "B", "C", "D", "E"]
    assert [event.event_type for event in reconstructed.keyboard_events] == [KeyboardEventType.DOWN] * 5
    assert [event.button for event in reconstructed.mouse_button_events] == [MouseButton.LEFT, MouseButton.RIGHT]
    assert reconstructed.scroll_events == ()


def test_no_action_is_valid_slot_but_pad_is_sequence_padding_not_noop() -> None:
    tokenizer = ActionTokenizer()
    mouse_zero = "MOUSE_MOVE_BIN_24_24"
    no_op_tokens = (mouse_zero, *(NO_ACTION for _ in range(8)))

    no_op_bin = tokenizer.detokenize_bin(no_op_tokens, start_ns=0, end_ns=ns_from_ms(50))

    assert no_op_bin.mouse_dx == 0
    assert no_op_bin.mouse_dy == 0
    assert no_op_bin.discrete_events == ()

    padded_tokens = (mouse_zero, PAD_ACTION, *(NO_ACTION for _ in range(7)))
    with pytest.raises(ValueError, match="PAD_ACTION is sequence padding"):
        tokenizer.detokenize_bin(padded_tokens, start_ns=0, end_ns=ns_from_ms(50))

    allowed = tokenizer.detokenize_bin(
        padded_tokens,
        start_ns=0,
        end_ns=ns_from_ms(50),
        allow_pad=True,
    )
    assert allowed.discrete_events == ()


def test_raw_prediction_tokens_get_deterministic_in_bin_timestamps() -> None:
    tokenizer = ActionTokenizer()
    raw_tokens = (
        "MOUSE_MOVE_BIN_24_24",
        "KEY_DOWN_SPACE",
        "MOUSE_LEFT_DOWN",
        *(NO_ACTION for _ in range(6)),
    )

    reconstructed = tokenizer.detokenize_bin(raw_tokens, start_ns=ns_from_ms(100), end_ns=ns_from_ms(150))

    assert [(event.family.value, event.timestamp_ns) for event in reconstructed.discrete_events] == [
        ("keyboard", 105_555_556),
        ("mouse_button", 111_111_111),
    ]
