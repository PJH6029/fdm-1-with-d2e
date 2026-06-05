"""Prediction-token to canonical-event round-trip helpers.

These utilities intentionally avoid MCAP writer dependencies. They reconstruct
canonical event dataclasses and dependency-light dictionaries with MCAP/OWAMcap
field names that later writer/evaluator adapters can consume.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from fdm_1_with_d2e.data.types import (
    DEFAULT_BIN_WIDTH_NS,
    ActionBin,
    CanonicalInputEvent,
    EventFamily,
    KeyboardEvent,
    MouseButtonEvent,
    MouseMoveEvent,
    ScrollEvent,
    event_sort_key,
)
from fdm_1_with_d2e.tokenization.actions import (
    DEFAULT_ACTION_TOKENIZER,
    ActionTokenizer,
    TokenizedActionBin,
    TokenizedActionSequence,
)


def action_bin_to_canonical_events(
    action_bin: ActionBin,
    *,
    include_zero_mouse: bool = False,
) -> tuple[CanonicalInputEvent, ...]:
    """Convert a reconstructed action bin to timestamp-sorted canonical events."""

    events: list[CanonicalInputEvent] = []
    if include_zero_mouse or action_bin.mouse_dx != 0 or action_bin.mouse_dy != 0:
        events.append(
            MouseMoveEvent(
                timestamp_ns=action_bin.start_ns,
                dx=action_bin.mouse_dx,
                dy=action_bin.mouse_dy,
                source_fields=("dx", "dy"),
            )
        )
    events.extend(action_bin.keyboard_events)
    events.extend(action_bin.mouse_button_events)
    events.extend(action_bin.scroll_events)
    return tuple(sorted(events, key=event_sort_key))


def tokenized_bins_to_action_bins(
    tokenized_bins: TokenizedActionSequence | Iterable[TokenizedActionBin | Sequence[str]],
    *,
    tokenizer: ActionTokenizer = DEFAULT_ACTION_TOKENIZER,
    start_ns: int = 0,
    bin_width_ns: int = DEFAULT_BIN_WIDTH_NS,
    allow_pad: bool = False,
    allow_mask: bool = False,
) -> tuple[ActionBin, ...]:
    """Reconstruct action bins from tokenized bins, per-bin tokens, or a sequence object."""

    if isinstance(tokenized_bins, TokenizedActionSequence):
        iterable: Iterable[TokenizedActionBin | Sequence[str]] = tokenized_bins.bins
    else:
        iterable = tokenized_bins
    return tokenizer.detokenize_bins(
        iterable,
        start_ns=start_ns,
        bin_width_ns=bin_width_ns,
        allow_pad=allow_pad,
        allow_mask=allow_mask,
    )


def tokenized_bins_to_canonical_events(
    tokenized_bins: TokenizedActionSequence | Iterable[TokenizedActionBin | Sequence[str]],
    *,
    tokenizer: ActionTokenizer = DEFAULT_ACTION_TOKENIZER,
    start_ns: int = 0,
    bin_width_ns: int = DEFAULT_BIN_WIDTH_NS,
    include_zero_mouse: bool = False,
    allow_pad: bool = False,
    allow_mask: bool = False,
) -> tuple[CanonicalInputEvent, ...]:
    """Reconstruct timestamp-sorted canonical events from action predictions."""

    action_bins = tokenized_bins_to_action_bins(
        tokenized_bins,
        tokenizer=tokenizer,
        start_ns=start_ns,
        bin_width_ns=bin_width_ns,
        allow_pad=allow_pad,
        allow_mask=allow_mask,
    )
    events: list[CanonicalInputEvent] = []
    for action_bin in action_bins:
        events.extend(action_bin_to_canonical_events(action_bin, include_zero_mouse=include_zero_mouse))
    return tuple(sorted(events, key=event_sort_key))


def canonical_event_to_writer_record(event: CanonicalInputEvent) -> dict[str, Any]:
    """Return a dependency-light MCAP/OWAMcap-compatible event dictionary."""

    base: dict[str, Any] = {
        "timestamp_ns": event.timestamp_ns,
        "family": event.family.value,
    }
    if isinstance(event, MouseMoveEvent):
        return {
            **base,
            "topic": "mouse_move",
            "dx": event.dx,
            "dy": event.dy,
            # Include both field conventions seen in D2E/OWAMcap snippets and
            # the public evaluator path so later adapters can choose either.
            "last_x": event.dx,
            "last_y": event.dy,
        }
    if isinstance(event, KeyboardEvent):
        return {
            **base,
            "topic": "keyboard",
            "key": event.key,
            "event_type": event.event_type.value,
        }
    if isinstance(event, MouseButtonEvent):
        return {
            **base,
            "topic": "mouse_button",
            "button": event.button.value,
            "event_type": event.event_type.value,
        }
    if isinstance(event, ScrollEvent):
        return {
            **base,
            "topic": "scroll",
            "delta_x": event.delta_x,
            "delta_y": event.delta_y,
            "directions": tuple(direction.value for direction in event.directions),
        }
    raise TypeError(f"unsupported writer event type: {type(event)!r}")


def canonical_events_to_writer_records(
    events: Iterable[CanonicalInputEvent],
) -> tuple[dict[str, Any], ...]:
    """Convert canonical events to sorted writer-compatible dictionaries."""

    return tuple(canonical_event_to_writer_record(event) for event in sorted(events, key=event_sort_key))


def tokenized_bins_to_writer_records(
    tokenized_bins: TokenizedActionSequence | Iterable[TokenizedActionBin | Sequence[str]],
    *,
    tokenizer: ActionTokenizer = DEFAULT_ACTION_TOKENIZER,
    start_ns: int = 0,
    bin_width_ns: int = DEFAULT_BIN_WIDTH_NS,
    include_zero_mouse: bool = False,
    allow_pad: bool = False,
    allow_mask: bool = False,
) -> tuple[dict[str, Any], ...]:
    """Reconstruct MCAP-compatible event records from predicted action tokens."""

    return canonical_events_to_writer_records(
        tokenized_bins_to_canonical_events(
            tokenized_bins,
            tokenizer=tokenizer,
            start_ns=start_ns,
            bin_width_ns=bin_width_ns,
            include_zero_mouse=include_zero_mouse,
            allow_pad=allow_pad,
            allow_mask=allow_mask,
        )
    )


__all__ = [
    "action_bin_to_canonical_events",
    "canonical_event_to_writer_record",
    "canonical_events_to_writer_records",
    "tokenized_bins_to_action_bins",
    "tokenized_bins_to_canonical_events",
    "tokenized_bins_to_writer_records",
]
