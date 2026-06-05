"""Canonical Phase 0 action tokens and mouse quantization.

The tokenizer uses one compound mouse token plus a fixed number of sparse event
slots per 50ms bin. Mouse bins are intentionally dependency-light and
reconstructable: one zero bin plus 24 exponentially-spaced bins per sign.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field
from enum import Enum
import math
import re
from collections.abc import Iterable

from fdm_1_with_d2e.data.types import (
    KeyboardEvent,
    KeyboardEventType,
    MouseButton,
    MouseButtonEvent,
    MouseButtonEventType,
    ScrollDirection,
    ScrollEvent,
)

MASK_ACTION = "MASK_ACTION"
NO_ACTION = "NO_ACTION"
PAD_ACTION = "PAD_ACTION"
BOS_ACTION = "BOS_ACTION"
EOS_ACTION = "EOS_ACTION"
EVENT_OVERFLOW = "EVENT_OVERFLOW"

SPECIAL_TOKENS: tuple[str, ...] = (
    MASK_ACTION,
    NO_ACTION,
    PAD_ACTION,
    BOS_ACTION,
    EOS_ACTION,
    EVENT_OVERFLOW,
)
SPECIAL_TOKEN_SET = frozenset(SPECIAL_TOKENS)

DEFAULT_SPARSE_EVENT_SLOTS = 8
DEFAULT_MOUSE_BINS_PER_AXIS = 49
DEFAULT_MOUSE_SIGNED_BINS_PER_SIDE = (DEFAULT_MOUSE_BINS_PER_AXIS - 1) // 2
DEFAULT_MOUSE_ZERO_BIN_INDEX = DEFAULT_MOUSE_SIGNED_BINS_PER_SIDE
DEFAULT_MOUSE_MAX_ABS_DELTA = 4096

_MOUSE_TOKEN_RE = re.compile(r"^MOUSE_MOVE_BIN_(?P<x>\d+)_(?P<y>\d+)$")
_KEY_DOWN_PREFIX = "KEY_DOWN_"
_KEY_UP_PREFIX = "KEY_UP_"
_MOUSE_BUTTON_RE = re.compile(r"^MOUSE_(?P<button>LEFT|RIGHT|MIDDLE)_(?P<transition>DOWN|UP)$")
_SCROLL_PREFIX = "SCROLL_"


class ActionTokenFamily(str, Enum):
    """Token families used for validation and diagnostics."""

    SPECIAL = "special"
    MOUSE_MOVE = "mouse_move"
    KEYBOARD = "keyboard"
    MOUSE_BUTTON = "mouse_button"
    SCROLL = "scroll"


@dataclass(frozen=True, slots=True)
class MouseAxisBin:
    """One signed axis-bin assignment and its representative delta."""

    index: int
    label: str
    representative_delta: int


@dataclass(frozen=True, slots=True)
class MouseMoveBin:
    """Compound mouse-bin assignment for a 50ms aggregate delta."""

    x: MouseAxisBin
    y: MouseAxisBin

    @property
    def token(self) -> str:
        return f"MOUSE_MOVE_BIN_{self.x.label}_{self.y.label}"

    @property
    def representative_delta(self) -> tuple[int, int]:
        return (self.x.representative_delta, self.y.representative_delta)


@dataclass(frozen=True, slots=True)
class MouseAxisQuantizer:
    """Signed exponential quantizer with one zero bin and mirrored signs.

    ``positive_edges`` are inclusive upper bounds for magnitudes ``>= 1``.
    Values larger than the final edge saturate to the largest bin. Bin indices
    are ordered from largest negative magnitude to largest positive magnitude:
    ``0..23`` negative, ``24`` zero, and ``25..48`` positive by default.
    """

    positive_edges: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.positive_edges:
            raise ValueError("positive_edges must not be empty")
        previous = 0
        for edge in self.positive_edges:
            if edge <= previous:
                raise ValueError("positive_edges must be strictly increasing positive integers")
            previous = edge

    @classmethod
    def default(cls, *, max_abs_delta: int = DEFAULT_MOUSE_MAX_ABS_DELTA) -> "MouseAxisQuantizer":
        """Create the default 24-bin-per-side exponential axis quantizer."""

        return cls(exponential_positive_edges(DEFAULT_MOUSE_SIGNED_BINS_PER_SIDE, max_abs_delta))

    @classmethod
    def fit_from_deltas(
        cls,
        deltas: Iterable[int | float],
        *,
        bin_count_per_side: int = DEFAULT_MOUSE_SIGNED_BINS_PER_SIDE,
        minimum_max_abs_delta: int = 1,
    ) -> "MouseAxisQuantizer":
        """Fit exponential edges from training-split deltas only.

        This keeps the Phase 0 contract explicit without adding a statistics
        dependency: the largest observed absolute training delta defines the
        target saturated edge; very small ranges are expanded as needed to keep
        all signed bins strict and non-empty.
        """

        max_abs = minimum_max_abs_delta
        for delta in deltas:
            max_abs = max(max_abs, int(abs(round(delta))))
        return cls(exponential_positive_edges(bin_count_per_side, max_abs))

    @property
    def bin_count_per_side(self) -> int:
        return len(self.positive_edges)

    @property
    def bins_per_axis(self) -> int:
        return 2 * self.bin_count_per_side + 1

    @property
    def zero_bin_index(self) -> int:
        return self.bin_count_per_side

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(str(index) for index in range(self.bins_per_axis))

    def quantize(self, delta: int | float) -> MouseAxisBin:
        """Map a signed delta to one of the fixed axis bins."""

        value = int(round(delta))
        if value == 0:
            return MouseAxisBin(self.zero_bin_index, str(self.zero_bin_index), 0)

        magnitude = abs(value)
        rank = bisect_left(self.positive_edges, magnitude)
        if rank >= self.bin_count_per_side:
            rank = self.bin_count_per_side - 1
        if value > 0:
            index = self.zero_bin_index + 1 + rank
            representative = self._representative_for_positive_rank(rank)
        else:
            index = self.zero_bin_index - 1 - rank
            representative = -self._representative_for_positive_rank(rank)
        return MouseAxisBin(index=index, label=str(index), representative_delta=representative)

    def dequantize(self, index_or_label: int | str) -> int:
        """Return the deterministic representative delta for an axis bin."""

        index = self.parse_bin_label(index_or_label)
        if index == self.zero_bin_index:
            return 0
        if index > self.zero_bin_index:
            rank = index - self.zero_bin_index - 1
            return self._representative_for_positive_rank(rank)
        rank = self.zero_bin_index - 1 - index
        return -self._representative_for_positive_rank(rank)

    def parse_bin_label(self, index_or_label: int | str) -> int:
        """Parse and range-check a numeric bin label."""

        try:
            index = int(index_or_label)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"mouse bin label must be an integer index: {index_or_label!r}") from exc
        if index < 0 or index >= self.bins_per_axis:
            raise ValueError(f"mouse bin index {index} outside [0, {self.bins_per_axis})")
        return index

    def positive_representative(self, rank: int) -> int:
        """Return the positive representative for a zero-based positive-bin rank."""

        if rank < 0 or rank >= self.bin_count_per_side:
            raise ValueError(f"positive rank {rank} outside [0, {self.bin_count_per_side})")
        return self._representative_for_positive_rank(rank)

    def _representative_for_positive_rank(self, rank: int) -> int:
        lower = 1 if rank == 0 else self.positive_edges[rank - 1] + 1
        upper = self.positive_edges[rank]
        return int(round((lower + upper) / 2))


@dataclass(frozen=True, slots=True)
class MouseQuantizer:
    """Compound X/Y mouse quantizer for ``MOUSE_MOVE_BIN_<x>_<y>`` tokens."""

    x_axis: MouseAxisQuantizer
    y_axis: MouseAxisQuantizer

    @classmethod
    def default(cls, *, max_abs_delta: int = DEFAULT_MOUSE_MAX_ABS_DELTA) -> "MouseQuantizer":
        axis = MouseAxisQuantizer.default(max_abs_delta=max_abs_delta)
        return cls(x_axis=axis, y_axis=axis)

    @classmethod
    def fit_from_training_deltas(
        cls,
        dx_values: Iterable[int | float],
        dy_values: Iterable[int | float],
        *,
        minimum_max_abs_delta: int = 1,
    ) -> "MouseQuantizer":
        """Fit mirrored exponential X/Y quantizers from training-split deltas."""

        return cls(
            x_axis=MouseAxisQuantizer.fit_from_deltas(
                dx_values,
                minimum_max_abs_delta=minimum_max_abs_delta,
            ),
            y_axis=MouseAxisQuantizer.fit_from_deltas(
                dy_values,
                minimum_max_abs_delta=minimum_max_abs_delta,
            ),
        )

    @property
    def bins_per_axis(self) -> int:
        if self.x_axis.bins_per_axis != self.y_axis.bins_per_axis:
            raise ValueError("x_axis and y_axis must use the same bin count")
        return self.x_axis.bins_per_axis

    @property
    def zero_bin_index(self) -> int:
        if self.x_axis.zero_bin_index != self.y_axis.zero_bin_index:
            raise ValueError("x_axis and y_axis must use the same zero index")
        return self.x_axis.zero_bin_index

    def quantize(self, dx: int | float, dy: int | float) -> MouseMoveBin:
        return MouseMoveBin(x=self.x_axis.quantize(dx), y=self.y_axis.quantize(dy))

    def token_for_delta(self, dx: int | float, dy: int | float) -> str:
        return self.quantize(dx, dy).token

    def parse_token(self, token: str) -> MouseMoveBin:
        match = _MOUSE_TOKEN_RE.match(token)
        if match is None:
            raise ValueError(f"not a compound mouse token: {token!r}")
        x_index = self.x_axis.parse_bin_label(match.group("x"))
        y_index = self.y_axis.parse_bin_label(match.group("y"))
        return MouseMoveBin(
            x=MouseAxisBin(x_index, str(x_index), self.x_axis.dequantize(x_index)),
            y=MouseAxisBin(y_index, str(y_index), self.y_axis.dequantize(y_index)),
        )

    def dequantize_token(self, token: str) -> tuple[int, int]:
        return self.parse_token(token).representative_delta

    def all_mouse_tokens(self) -> tuple[str, ...]:
        labels = tuple(range(self.bins_per_axis))
        return tuple(f"MOUSE_MOVE_BIN_{x}_{y}" for x in labels for y in labels)


@dataclass(frozen=True, slots=True)
class ParsedKeyboardToken:
    key: str
    event_type: KeyboardEventType


@dataclass(frozen=True, slots=True)
class ParsedMouseButtonToken:
    button: MouseButton
    event_type: MouseButtonEventType


@dataclass(frozen=True, slots=True)
class ActionVocabulary:
    """Token string factory/parser for canonical D2E input events."""

    mouse_quantizer: MouseQuantizer = field(default_factory=MouseQuantizer.default)

    @property
    def special_tokens(self) -> tuple[str, ...]:
        return SPECIAL_TOKENS

    @property
    def mouse_tokens(self) -> tuple[str, ...]:
        return self.mouse_quantizer.all_mouse_tokens()

    def token_family(self, token: str) -> ActionTokenFamily:
        if token in SPECIAL_TOKEN_SET:
            return ActionTokenFamily.SPECIAL
        if _MOUSE_TOKEN_RE.match(token):
            self.mouse_quantizer.parse_token(token)
            return ActionTokenFamily.MOUSE_MOVE
        if token.startswith(_KEY_DOWN_PREFIX) or token.startswith(_KEY_UP_PREFIX):
            self.parse_keyboard_token(token)
            return ActionTokenFamily.KEYBOARD
        if _MOUSE_BUTTON_RE.match(token):
            self.parse_mouse_button_token(token)
            return ActionTokenFamily.MOUSE_BUTTON
        if token.startswith(_SCROLL_PREFIX):
            self.parse_scroll_token(token)
            return ActionTokenFamily.SCROLL
        raise ValueError(f"unknown action token: {token!r}")

    def mouse_token(self, dx: int | float, dy: int | float) -> str:
        return self.mouse_quantizer.token_for_delta(dx, dy)

    def parse_mouse_token(self, token: str) -> MouseMoveBin:
        return self.mouse_quantizer.parse_token(token)

    def keyboard_token(self, event: KeyboardEvent) -> str:
        key = _validate_key(event.key)
        if event.event_type is KeyboardEventType.DOWN:
            return f"{_KEY_DOWN_PREFIX}{key}"
        if event.event_type is KeyboardEventType.UP:
            return f"{_KEY_UP_PREFIX}{key}"
        raise ValueError(f"unsupported keyboard event type: {event.event_type!r}")

    def parse_keyboard_token(self, token: str) -> ParsedKeyboardToken:
        if token.startswith(_KEY_DOWN_PREFIX):
            key = token[len(_KEY_DOWN_PREFIX) :]
            event_type = KeyboardEventType.DOWN
        elif token.startswith(_KEY_UP_PREFIX):
            key = token[len(_KEY_UP_PREFIX) :]
            event_type = KeyboardEventType.UP
        else:
            raise ValueError(f"not a keyboard token: {token!r}")
        return ParsedKeyboardToken(key=_validate_key(key), event_type=event_type)

    def mouse_button_token(self, event: MouseButtonEvent) -> str:
        return f"MOUSE_{event.button.value.upper()}_{event.event_type.value.upper()}"

    def parse_mouse_button_token(self, token: str) -> ParsedMouseButtonToken:
        match = _MOUSE_BUTTON_RE.match(token)
        if match is None:
            raise ValueError(f"not a mouse-button token: {token!r}")
        return ParsedMouseButtonToken(
            button=MouseButton(match.group("button").lower()),
            event_type=MouseButtonEventType(match.group("transition").lower()),
        )

    def scroll_tokens(self, event: ScrollEvent) -> tuple[str, ...]:
        return tuple(self.scroll_token(direction) for direction in event.directions)

    def scroll_token(self, direction: ScrollDirection) -> str:
        return f"SCROLL_{direction.value.upper()}"

    def parse_scroll_token(self, token: str) -> ScrollDirection:
        if not token.startswith(_SCROLL_PREFIX):
            raise ValueError(f"not a scroll token: {token!r}")
        suffix = token[len(_SCROLL_PREFIX) :].lower()
        try:
            return ScrollDirection(suffix)
        except ValueError as exc:
            raise ValueError(f"unsupported scroll direction token: {token!r}") from exc


def exponential_positive_edges(bin_count_per_side: int, max_abs_delta: int) -> tuple[int, ...]:
    """Return strictly increasing exponential positive-bin upper bounds."""

    if bin_count_per_side <= 0:
        raise ValueError("bin_count_per_side must be positive")
    if max_abs_delta <= 0:
        raise ValueError("max_abs_delta must be positive")

    log_max = math.log(max_abs_delta)
    edges: list[int] = []
    previous = 0
    for index in range(1, bin_count_per_side + 1):
        edge = int(round(math.exp(log_max * index / bin_count_per_side)))
        edge = max(edge, previous + 1)
        if index == bin_count_per_side:
            edge = max(edge, max_abs_delta)
        edges.append(edge)
        previous = edge
    return tuple(edges)


def is_special_token(token: str) -> bool:
    return token in SPECIAL_TOKEN_SET


def _validate_key(key: str) -> str:
    if not isinstance(key, str):
        raise TypeError("key must be a string")
    if not key:
        raise ValueError("key token suffix must not be empty")
    if any(character.isspace() for character in key):
        raise ValueError(f"key token suffix must not contain whitespace: {key!r}")
    return key


DEFAULT_MOUSE_QUANTIZER = MouseQuantizer.default()
DEFAULT_ACTION_VOCAB = ActionVocabulary(DEFAULT_MOUSE_QUANTIZER)

__all__ = [
    "ActionTokenFamily",
    "ActionVocabulary",
    "BOS_ACTION",
    "DEFAULT_ACTION_VOCAB",
    "DEFAULT_MOUSE_BINS_PER_AXIS",
    "DEFAULT_MOUSE_MAX_ABS_DELTA",
    "DEFAULT_MOUSE_QUANTIZER",
    "DEFAULT_MOUSE_SIGNED_BINS_PER_SIDE",
    "DEFAULT_MOUSE_ZERO_BIN_INDEX",
    "DEFAULT_SPARSE_EVENT_SLOTS",
    "EOS_ACTION",
    "EVENT_OVERFLOW",
    "MASK_ACTION",
    "NO_ACTION",
    "PAD_ACTION",
    "ParsedKeyboardToken",
    "ParsedMouseButtonToken",
    "MouseAxisBin",
    "MouseAxisQuantizer",
    "MouseMoveBin",
    "MouseQuantizer",
    "SPECIAL_TOKEN_SET",
    "SPECIAL_TOKENS",
    "exponential_positive_edges",
    "is_special_token",
]
