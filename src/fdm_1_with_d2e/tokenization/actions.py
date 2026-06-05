"""Action-bin tokenization and de-tokenization for Phase 0 D2E actions."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from fdm_1_with_d2e.data.types import (
    DEFAULT_BIN_WIDTH_NS,
    ActionBin,
    DiscreteInputEvent,
    KeyboardEvent,
    KeyboardEventType,
    MouseButtonEvent,
    MouseButtonEventType,
    ScrollDirection,
    ScrollEvent,
    event_sort_key,
)
from fdm_1_with_d2e.tokenization.action_vocab import (
    DEFAULT_ACTION_VOCAB,
    DEFAULT_SPARSE_EVENT_SLOTS,
    EVENT_OVERFLOW,
    MASK_ACTION,
    NO_ACTION,
    PAD_ACTION,
    ActionVocabulary,
)


@dataclass(frozen=True, slots=True)
class ActionSlot:
    """One fixed sparse-event slot in a tokenized 50ms action bin."""

    index: int
    token: str
    timestamp_ns: int | None = None
    source_family: str | None = None

    @property
    def is_no_action(self) -> bool:
        return self.token == NO_ACTION

    @property
    def is_overflow_marker(self) -> bool:
        return self.token == EVENT_OVERFLOW


@dataclass(frozen=True, slots=True)
class OverflowRecord:
    """Accounting for sparse events dropped due to fixed ``K`` capacity."""

    bin_index: int
    original_event_count: int
    retained_event_count: int
    dropped_event_count: int
    retained_tokens: tuple[str, ...]
    dropped_tokens: tuple[str, ...]
    overflow_token: str = EVENT_OVERFLOW


@dataclass(frozen=True, slots=True)
class TokenizedActionBin:
    """Fixed token representation for one canonical 50ms action bin."""

    bin_index: int
    start_ns: int
    end_ns: int
    mouse_token: str
    event_slots: tuple[ActionSlot, ...]
    original_mouse_dx: int
    original_mouse_dy: int
    overflow: OverflowRecord | None = None

    @property
    def tokens(self) -> tuple[str, ...]:
        return (self.mouse_token, *(slot.token for slot in self.event_slots))

    @property
    def event_tokens(self) -> tuple[str, ...]:
        return tuple(slot.token for slot in self.event_slots)

    @property
    def has_overflow(self) -> bool:
        return self.overflow is not None


@dataclass(frozen=True, slots=True)
class TokenizedActionSequence:
    """Tokenized bins plus aggregate overflow diagnostics."""

    bins: tuple[TokenizedActionBin, ...]
    slots_per_bin: int = DEFAULT_SPARSE_EVENT_SLOTS

    @property
    def tokens(self) -> tuple[str, ...]:
        return tuple(token for tokenized_bin in self.bins for token in tokenized_bin.tokens)

    @property
    def overflow_records(self) -> tuple[OverflowRecord, ...]:
        return tuple(tokenized_bin.overflow for tokenized_bin in self.bins if tokenized_bin.overflow is not None)

    @property
    def overflow_bin_count(self) -> int:
        return len(self.overflow_records)

    @property
    def overflow_bin_fraction(self) -> float:
        if not self.bins:
            return 0.0
        return self.overflow_bin_count / len(self.bins)


@dataclass(frozen=True, slots=True)
class _CandidateEventToken:
    token: str
    timestamp_ns: int
    source_event: DiscreteInputEvent
    overflow_priority: int
    tie_breaker: tuple[int, int, str, str]


class ActionTokenizer:
    """Tokenize/de-tokenize canonical action bins with fixed sparse slots."""

    def __init__(
        self,
        *,
        vocab: ActionVocabulary = DEFAULT_ACTION_VOCAB,
        slots_per_bin: int = DEFAULT_SPARSE_EVENT_SLOTS,
    ) -> None:
        if slots_per_bin <= 0:
            raise ValueError("slots_per_bin must be positive")
        self.vocab = vocab
        self.slots_per_bin = slots_per_bin

    @property
    def tokens_per_bin(self) -> int:
        return 1 + self.slots_per_bin

    def tokenize_bin(self, action_bin: ActionBin) -> TokenizedActionBin:
        """Tokenize one ``ActionBin`` as ``[mouse_token] + K event slots``."""

        mouse_token = self.vocab.mouse_token(action_bin.mouse_dx, action_bin.mouse_dy)
        candidates = tuple(self._candidate_event_tokens(action_bin))
        selected, overflow = self._select_sparse_events(action_bin.index, candidates)

        slots = [
            ActionSlot(
                index=index,
                token=candidate.token,
                timestamp_ns=candidate.timestamp_ns,
                source_family=candidate.source_event.family.value,
            )
            for index, candidate in enumerate(selected)
        ]
        if overflow is not None:
            slots.append(ActionSlot(index=len(slots), token=EVENT_OVERFLOW, timestamp_ns=None, source_family=None))
        while len(slots) < self.slots_per_bin:
            slots.append(ActionSlot(index=len(slots), token=NO_ACTION, timestamp_ns=None, source_family=None))

        return TokenizedActionBin(
            bin_index=action_bin.index,
            start_ns=action_bin.start_ns,
            end_ns=action_bin.end_ns,
            mouse_token=mouse_token,
            event_slots=tuple(slots),
            original_mouse_dx=action_bin.mouse_dx,
            original_mouse_dy=action_bin.mouse_dy,
            overflow=overflow,
        )

    def tokenize_bins(self, action_bins: Iterable[ActionBin]) -> TokenizedActionSequence:
        return TokenizedActionSequence(
            bins=tuple(self.tokenize_bin(action_bin) for action_bin in action_bins),
            slots_per_bin=self.slots_per_bin,
        )

    def detokenize_bin(
        self,
        tokenized: TokenizedActionBin | Sequence[str],
        *,
        bin_index: int | None = None,
        start_ns: int | None = None,
        end_ns: int | None = None,
        allow_pad: bool = False,
        allow_mask: bool = False,
    ) -> ActionBin:
        """Reconstruct a canonical ``ActionBin`` from tokens.

        ``NO_ACTION`` is a valid no-op slot inside a real 50ms bin. ``PAD_ACTION``
        is sequence-packing padding and is rejected by default so padding is not
        silently interpreted as a valid no-op action.
        """

        if isinstance(tokenized, TokenizedActionBin):
            tokens = tokenized.tokens
            slot_metadata = tokenized.event_slots
            resolved_index = tokenized.bin_index if bin_index is None else bin_index
            resolved_start = tokenized.start_ns if start_ns is None else start_ns
            resolved_end = tokenized.end_ns if end_ns is None else end_ns
        else:
            tokens = tuple(tokenized)
            slot_metadata = ()
            resolved_index = 0 if bin_index is None else bin_index
            resolved_start = 0 if start_ns is None else start_ns
            resolved_end = resolved_start + DEFAULT_BIN_WIDTH_NS if end_ns is None else end_ns

        if len(tokens) != self.tokens_per_bin:
            raise ValueError(f"expected {self.tokens_per_bin} tokens per bin, got {len(tokens)}")
        if resolved_end <= resolved_start:
            raise ValueError("end_ns must be greater than start_ns")

        mouse_dx, mouse_dy = self.vocab.mouse_quantizer.dequantize_token(tokens[0])
        keyboard_events: list[KeyboardEvent] = []
        mouse_button_events: list[MouseButtonEvent] = []
        scroll_events: list[ScrollEvent] = []

        for slot_index, token in enumerate(tokens[1:]):
            if token == NO_ACTION:
                continue
            if token == EVENT_OVERFLOW:
                # The marker is an explicit loss/accounting token, not a
                # reconstructable input event.
                continue
            if token == PAD_ACTION:
                if allow_pad:
                    continue
                raise ValueError("PAD_ACTION is sequence padding, not a valid in-bin no-op slot")
            if token == MASK_ACTION:
                if allow_mask:
                    continue
                raise ValueError("MASK_ACTION cannot be reconstructed without a prediction")

            timestamp_ns = self._event_timestamp_for_slot(
                slot_index,
                resolved_start,
                resolved_end,
                slot_metadata,
            )
            event = self._event_from_token(token, timestamp_ns)
            if isinstance(event, KeyboardEvent):
                keyboard_events.append(event)
            elif isinstance(event, MouseButtonEvent):
                mouse_button_events.append(event)
            elif isinstance(event, ScrollEvent):
                scroll_events.append(event)
            else:  # pragma: no cover - defensive for future union expansion.
                raise TypeError(f"unexpected reconstructed event type: {type(event)!r}")

        return ActionBin(
            index=resolved_index,
            start_ns=resolved_start,
            end_ns=resolved_end,
            mouse_dx=mouse_dx,
            mouse_dy=mouse_dy,
            keyboard_events=tuple(sorted(keyboard_events, key=event_sort_key)),
            mouse_button_events=tuple(sorted(mouse_button_events, key=event_sort_key)),
            scroll_events=tuple(sorted(scroll_events, key=event_sort_key)),
        )

    def detokenize_bins(
        self,
        tokenized_bins: TokenizedActionSequence | Iterable[TokenizedActionBin | Sequence[str]],
        *,
        start_ns: int = 0,
        bin_width_ns: int = DEFAULT_BIN_WIDTH_NS,
        allow_pad: bool = False,
        allow_mask: bool = False,
    ) -> tuple[ActionBin, ...]:
        """Reconstruct bins from tokenized bins or raw per-bin token sequences."""

        iterable: Iterable[TokenizedActionBin | Sequence[str]]
        if isinstance(tokenized_bins, TokenizedActionSequence):
            iterable = tokenized_bins.bins
        else:
            iterable = tokenized_bins

        reconstructed: list[ActionBin] = []
        for fallback_index, tokenized in enumerate(iterable):
            if isinstance(tokenized, TokenizedActionBin):
                reconstructed.append(
                    self.detokenize_bin(tokenized, allow_pad=allow_pad, allow_mask=allow_mask)
                )
            else:
                bin_start = start_ns + fallback_index * bin_width_ns
                reconstructed.append(
                    self.detokenize_bin(
                        tokenized,
                        bin_index=fallback_index,
                        start_ns=bin_start,
                        end_ns=bin_start + bin_width_ns,
                        allow_pad=allow_pad,
                        allow_mask=allow_mask,
                    )
                )
        return tuple(reconstructed)

    def detokenize_flat_sequence(
        self,
        tokens: Sequence[str],
        *,
        start_ns: int = 0,
        bin_width_ns: int = DEFAULT_BIN_WIDTH_NS,
        allow_pad: bool = False,
        allow_mask: bool = False,
    ) -> tuple[ActionBin, ...]:
        """Reconstruct bins from a flat sequence of fixed-width action tokens."""

        if len(tokens) % self.tokens_per_bin != 0:
            raise ValueError(
                f"flat token sequence length {len(tokens)} is not divisible by tokens_per_bin={self.tokens_per_bin}"
            )
        per_bin = tuple(
            tuple(tokens[index : index + self.tokens_per_bin])
            for index in range(0, len(tokens), self.tokens_per_bin)
        )
        return self.detokenize_bins(
            per_bin,
            start_ns=start_ns,
            bin_width_ns=bin_width_ns,
            allow_pad=allow_pad,
            allow_mask=allow_mask,
        )

    def _candidate_event_tokens(self, action_bin: ActionBin) -> list[_CandidateEventToken]:
        candidates: list[_CandidateEventToken] = []
        for event in action_bin.keyboard_events:
            priority = 1 if event.event_type is KeyboardEventType.DOWN else 2
            candidates.append(
                _CandidateEventToken(
                    token=self.vocab.keyboard_token(event),
                    timestamp_ns=event.timestamp_ns,
                    source_event=event,
                    overflow_priority=priority,
                    tie_breaker=event_sort_key(event),
                )
            )
        for event in action_bin.mouse_button_events:
            candidates.append(
                _CandidateEventToken(
                    token=self.vocab.mouse_button_token(event),
                    timestamp_ns=event.timestamp_ns,
                    source_event=event,
                    overflow_priority=0,
                    tie_breaker=event_sort_key(event),
                )
            )
        for event in action_bin.scroll_events:
            for direction_index, token in enumerate(self.vocab.scroll_tokens(event)):
                candidates.append(
                    _CandidateEventToken(
                        token=token,
                        timestamp_ns=event.timestamp_ns,
                        source_event=event,
                        overflow_priority=3,
                        tie_breaker=(*event_sort_key(event), str(direction_index)),
                    )
                )
        return sorted(candidates, key=lambda item: item.tie_breaker)

    def _select_sparse_events(
        self,
        bin_index: int,
        candidates: tuple[_CandidateEventToken, ...],
    ) -> tuple[tuple[_CandidateEventToken, ...], OverflowRecord | None]:
        if len(candidates) <= self.slots_per_bin:
            return candidates, None

        retained_capacity = self.slots_per_bin - 1  # Reserve one slot for EVENT_OVERFLOW.
        indexed_candidates = tuple(enumerate(candidates))
        priority_ordered = sorted(
            indexed_candidates,
            key=lambda item: (item[1].overflow_priority, item[1].tie_breaker, item[0]),
        )
        retained_indices = {index for index, _candidate in priority_ordered[:retained_capacity]}
        retained = tuple(candidate for index, candidate in indexed_candidates if index in retained_indices)
        dropped = tuple(candidate for index, candidate in indexed_candidates if index not in retained_indices)
        overflow = OverflowRecord(
            bin_index=bin_index,
            original_event_count=len(candidates),
            retained_event_count=len(retained),
            dropped_event_count=len(dropped),
            retained_tokens=tuple(candidate.token for candidate in retained),
            dropped_tokens=tuple(candidate.token for candidate in dropped),
        )
        return retained, overflow

    def _event_timestamp_for_slot(
        self,
        slot_index: int,
        start_ns: int,
        end_ns: int,
        metadata: Sequence[ActionSlot],
    ) -> int:
        if slot_index < len(metadata) and metadata[slot_index].timestamp_ns is not None:
            timestamp_ns = int(metadata[slot_index].timestamp_ns)
            if start_ns <= timestamp_ns < end_ns:
                return timestamp_ns
        duration = end_ns - start_ns
        offset = round((slot_index + 1) * duration / (self.slots_per_bin + 1))
        offset = max(0, min(duration - 1, offset))
        return start_ns + offset

    def _event_from_token(self, token: str, timestamp_ns: int) -> DiscreteInputEvent:
        family = self.vocab.token_family(token)
        if family.value == "keyboard":
            parsed = self.vocab.parse_keyboard_token(token)
            return KeyboardEvent(timestamp_ns=timestamp_ns, key=parsed.key, event_type=parsed.event_type)
        if family.value == "mouse_button":
            parsed = self.vocab.parse_mouse_button_token(token)
            return MouseButtonEvent(timestamp_ns=timestamp_ns, button=parsed.button, event_type=parsed.event_type)
        if family.value == "scroll":
            direction = self.vocab.parse_scroll_token(token)
            return _scroll_event_from_direction(timestamp_ns, direction)
        raise ValueError(f"token cannot be reconstructed as a sparse event: {token!r}")


def tokenize_action_bin(
    action_bin: ActionBin,
    *,
    tokenizer: ActionTokenizer | None = None,
) -> TokenizedActionBin:
    return (tokenizer or DEFAULT_ACTION_TOKENIZER).tokenize_bin(action_bin)


def tokenize_action_bins(
    action_bins: Iterable[ActionBin],
    *,
    tokenizer: ActionTokenizer | None = None,
) -> TokenizedActionSequence:
    return (tokenizer or DEFAULT_ACTION_TOKENIZER).tokenize_bins(action_bins)


def detokenize_action_bin(
    tokenized: TokenizedActionBin | Sequence[str],
    *,
    tokenizer: ActionTokenizer | None = None,
    **kwargs: object,
) -> ActionBin:
    return (tokenizer or DEFAULT_ACTION_TOKENIZER).detokenize_bin(tokenized, **kwargs)


def detokenize_flat_action_sequence(
    tokens: Sequence[str],
    *,
    tokenizer: ActionTokenizer | None = None,
    **kwargs: object,
) -> tuple[ActionBin, ...]:
    return (tokenizer or DEFAULT_ACTION_TOKENIZER).detokenize_flat_sequence(tokens, **kwargs)


def _scroll_event_from_direction(timestamp_ns: int, direction: ScrollDirection) -> ScrollEvent:
    if direction is ScrollDirection.UP:
        return ScrollEvent(timestamp_ns=timestamp_ns, delta_y=1)
    if direction is ScrollDirection.DOWN:
        return ScrollEvent(timestamp_ns=timestamp_ns, delta_y=-1)
    if direction is ScrollDirection.RIGHT:
        return ScrollEvent(timestamp_ns=timestamp_ns, delta_x=1)
    if direction is ScrollDirection.LEFT:
        return ScrollEvent(timestamp_ns=timestamp_ns, delta_x=-1)
    raise ValueError(f"unsupported scroll direction: {direction!r}")


DEFAULT_ACTION_TOKENIZER = ActionTokenizer()

__all__ = [
    "ActionSlot",
    "ActionTokenizer",
    "DEFAULT_ACTION_TOKENIZER",
    "OverflowRecord",
    "TokenizedActionBin",
    "TokenizedActionSequence",
    "detokenize_action_bin",
    "detokenize_flat_action_sequence",
    "tokenize_action_bin",
    "tokenize_action_bins",
]
