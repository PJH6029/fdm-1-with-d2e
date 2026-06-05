from __future__ import annotations

import pytest

from fdm_1_with_d2e.data import (
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
    DEFAULT_MOUSE_BINS_PER_AXIS,
    DEFAULT_MOUSE_ZERO_BIN_INDEX,
    ActionTokenFamily,
    ActionVocabulary,
    MouseAxisQuantizer,
    MouseQuantizer,
    exponential_positive_edges,
)


def test_default_mouse_quantizer_has_49_signed_exponential_bins_including_zero() -> None:
    quantizer = MouseQuantizer.default()

    assert quantizer.bins_per_axis == DEFAULT_MOUSE_BINS_PER_AXIS
    assert quantizer.zero_bin_index == DEFAULT_MOUSE_ZERO_BIN_INDEX
    assert quantizer.token_for_delta(0, 0) == "MOUSE_MOVE_BIN_24_24"
    assert quantizer.dequantize_token("MOUSE_MOVE_BIN_24_24") == (0, 0)

    positive_edges = quantizer.x_axis.positive_edges
    assert len(positive_edges) == 24
    assert all(left < right for left, right in zip(positive_edges, positive_edges[1:]))
    # Exponential, not linear: gaps grow by the high-magnitude tail.
    gaps = [right - left for left, right in zip(positive_edges, positive_edges[1:])]
    assert max(gaps) > min(gaps) * 10


def test_mouse_quantization_dequantizes_to_deterministic_representatives() -> None:
    axis = MouseAxisQuantizer.default()
    quantizer = MouseQuantizer(axis, axis)
    dx = axis.positive_representative(4)
    dy = -axis.positive_representative(7)

    token = quantizer.token_for_delta(dx, dy)

    assert token == "MOUSE_MOVE_BIN_29_16"
    assert quantizer.dequantize_token(token) == (dx, dy)
    assert quantizer.dequantize_token(quantizer.token_for_delta(10_000, -10_000)) == (
        axis.positive_representative(23),
        -axis.positive_representative(23),
    )


def test_fit_from_training_deltas_uses_training_max_for_saturated_edge() -> None:
    quantizer = MouseQuantizer.fit_from_training_deltas([0, 2, -7], [0, 12, -3])

    assert quantizer.x_axis.positive_edges[-1] >= 7
    assert quantizer.y_axis.positive_edges[-1] >= 12
    assert quantizer.x_axis.positive_edges[-1] == quantizer.x_axis.bin_count_per_side
    assert quantizer.y_axis.positive_edges[-1] == quantizer.y_axis.bin_count_per_side
    assert quantizer.dequantize_token(quantizer.token_for_delta(7, -12)) == (7, -12)


def test_event_token_factories_and_parsers_are_canonical() -> None:
    vocab = ActionVocabulary()

    keyboard = KeyboardEvent(timestamp_ns=ns_from_ms(1), key="Key_A", event_type=KeyboardEventType.DOWN)
    button = MouseButtonEvent(
        timestamp_ns=ns_from_ms(2),
        button=MouseButton.LEFT,
        event_type=MouseButtonEventType.UP,
    )
    scroll = ScrollEvent(timestamp_ns=ns_from_ms(3), delta_x=-1, delta_y=1)

    assert vocab.keyboard_token(keyboard) == "KEY_DOWN_Key_A"
    assert vocab.parse_keyboard_token("KEY_UP_SPACE").key == "SPACE"
    assert vocab.parse_keyboard_token("KEY_UP_SPACE").event_type is KeyboardEventType.UP
    assert vocab.mouse_button_token(button) == "MOUSE_LEFT_UP"
    assert vocab.parse_mouse_button_token("MOUSE_RIGHT_DOWN").button is MouseButton.RIGHT
    assert vocab.scroll_tokens(scroll) == ("SCROLL_UP", "SCROLL_LEFT")
    assert vocab.parse_scroll_token("SCROLL_DOWN") is ScrollDirection.DOWN

    assert vocab.token_family("KEY_DOWN_Key_A") is ActionTokenFamily.KEYBOARD
    assert vocab.token_family("MOUSE_LEFT_UP") is ActionTokenFamily.MOUSE_BUTTON
    assert vocab.token_family("SCROLL_RIGHT") is ActionTokenFamily.SCROLL

    with pytest.raises(ValueError, match="whitespace"):
        vocab.keyboard_token(KeyboardEvent(timestamp_ns=0, key="bad key", event_type=KeyboardEventType.DOWN))


def test_exponential_edges_reject_invalid_requests() -> None:
    with pytest.raises(ValueError):
        exponential_positive_edges(0, 100)
    with pytest.raises(ValueError):
        exponential_positive_edges(24, 0)
