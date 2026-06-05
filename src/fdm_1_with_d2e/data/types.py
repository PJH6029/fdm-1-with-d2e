"""Canonical D2E data, input-event, and 50ms timestep types.

The Phase 0 reader/binning contract intentionally keeps these types dependency
light so offline tests can exercise the same objects that later MCAP-backed
readers, tokenizers, evaluators, and harness adapters will share.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, Protocol

NANOSECONDS_PER_MILLISECOND = 1_000_000
NANOSECONDS_PER_SECOND = 1_000_000_000
DEFAULT_BIN_WIDTH_MS = 50
DEFAULT_BIN_WIDTH_NS = DEFAULT_BIN_WIDTH_MS * NANOSECONDS_PER_MILLISECOND
D2E_VIDEO_FPS = 60


class EventFamily(str, Enum):
    """Top-level canonical event families used by action binning."""

    KEYBOARD = "keyboard"
    MOUSE_MOVE = "mouse_move"
    MOUSE_BUTTON = "mouse_button"
    SCROLL = "scroll"
    SCREEN = "screen"


class KeyboardEventType(str, Enum):
    """Canonical keyboard transition types."""

    DOWN = "down"
    UP = "up"


class MouseButton(str, Enum):
    """Canonical mouse buttons required by the Phase 0 D2E action contract."""

    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class MouseButtonEventType(str, Enum):
    """Canonical mouse-button transition types."""

    DOWN = "down"
    UP = "up"


class ScrollDirection(str, Enum):
    """Directional scroll events before optional magnitude binning."""

    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


class ScreenEventType(str, Enum):
    """Optional screen-state diagnostics carried alongside input bins."""

    CURSOR_POSITION = "cursor_position"
    ACTIVE_WINDOW = "active_window"
    SCREEN_SIZE = "screen_size"


class VideoSamplingPolicy(str, Enum):
    """Policies for mapping source video frames to one visual timestep per bin."""

    CAUSAL_LATEST_FRAME = "causal_latest_frame_at_or_before_bin_start"
    WITHIN_BIN_FRAMES = "within_bin_frames_noncausal_pool"
    CENTER_FRAME_WITHIN_BIN = "center_frame_within_bin_noncausal"


class TimestampedEvent(Protocol):
    """Minimal protocol shared by canonical event dataclasses."""

    timestamp_ns: int

    @property
    def family(self) -> EventFamily:
        """Return the canonical event family."""


@dataclass(frozen=True, slots=True)
class D2ERecording:
    """A discovered labeled D2E recording represented as a video/event pair.

    Discovery is content-free: paths are paired by directory and stem under the
    labeled dataset tree; duration/checksum fields are intentionally absent here
    and belong to later manifest stories that may inspect file metadata/content.
    """

    game: str
    stem: str
    video_path: Path
    mcap_path: Path
    dataset_root: Path | None = None
    split: str = "labeled"
    duration_ns: int | None = None

    @property
    def recording_id(self) -> str:
        """Deterministic stable id from split, game path, and recording stem."""

        parts = [self.split]
        if self.game:
            parts.append(self.game)
        parts.append(self.stem)
        return "/".join(parts)

    @property
    def relative_video_path(self) -> Path:
        """Video path relative to the dataset root when available."""

        return _relative_to_or_self(self.video_path, self.dataset_root)

    @property
    def relative_mcap_path(self) -> Path:
        """MCAP path relative to the dataset root when available."""

        return _relative_to_or_self(self.mcap_path, self.dataset_root)


@dataclass(frozen=True, slots=True)
class KeyboardEvent:
    """A timestamped key press/release transition."""

    timestamp_ns: int
    key: str
    event_type: KeyboardEventType

    @property
    def family(self) -> EventFamily:
        return EventFamily.KEYBOARD


@dataclass(frozen=True, slots=True)
class MouseMoveEvent:
    """A raw HID mouse delta event normalized to dx/dy."""

    timestamp_ns: int
    dx: int
    dy: int
    source_fields: tuple[str, str] = ("dx", "dy")

    @property
    def family(self) -> EventFamily:
        return EventFamily.MOUSE_MOVE


@dataclass(frozen=True, slots=True)
class MouseButtonEvent:
    """A timestamped mouse-button down/up transition."""

    timestamp_ns: int
    button: MouseButton
    event_type: MouseButtonEventType

    @property
    def family(self) -> EventFamily:
        return EventFamily.MOUSE_BUTTON


@dataclass(frozen=True, slots=True)
class ScrollEvent:
    """A directional scroll event using raw horizontal/vertical deltas."""

    timestamp_ns: int
    delta_x: int = 0
    delta_y: int = 0

    @property
    def family(self) -> EventFamily:
        return EventFamily.SCROLL

    @property
    def directions(self) -> tuple[ScrollDirection, ...]:
        """Return canonical directional tokens implied by this scroll delta."""

        directions: list[ScrollDirection] = []
        if self.delta_y > 0:
            directions.append(ScrollDirection.UP)
        elif self.delta_y < 0:
            directions.append(ScrollDirection.DOWN)
        if self.delta_x > 0:
            directions.append(ScrollDirection.RIGHT)
        elif self.delta_x < 0:
            directions.append(ScrollDirection.LEFT)
        return tuple(directions)


@dataclass(frozen=True, slots=True)
class ScreenEvent:
    """Optional screen-state event for diagnostics or auxiliary heads."""

    timestamp_ns: int
    event_type: ScreenEventType
    value: Any

    @property
    def family(self) -> EventFamily:
        return EventFamily.SCREEN


DiscreteInputEvent = KeyboardEvent | MouseButtonEvent | ScrollEvent
CanonicalInputEvent = KeyboardEvent | MouseMoveEvent | MouseButtonEvent | ScrollEvent | ScreenEvent


@dataclass(frozen=True, slots=True)
class DroppedEvent:
    """Event that could not be assigned to the requested bin span."""

    timestamp_ns: int
    family: EventFamily
    reason: str


@dataclass(frozen=True, slots=True)
class ActionBin:
    """Canonical non-overlapping 50ms action bin.

    Bins use half-open intervals: ``[start_ns, end_ns)``. Events exactly on a
    bin boundary are assigned to the later bin; events at the requested stop
    timestamp are outside the requested range.
    """

    index: int
    start_ns: int
    end_ns: int
    mouse_dx: int = 0
    mouse_dy: int = 0
    keyboard_events: tuple[KeyboardEvent, ...] = ()
    mouse_button_events: tuple[MouseButtonEvent, ...] = ()
    scroll_events: tuple[ScrollEvent, ...] = ()
    screen_events: tuple[ScreenEvent, ...] = ()

    @property
    def duration_ns(self) -> int:
        return self.end_ns - self.start_ns

    @property
    def discrete_events(self) -> tuple[DiscreteInputEvent, ...]:
        """Sparse non-mouse-move events in deterministic timestamp order."""

        return tuple(
            sorted(
                (*self.keyboard_events, *self.mouse_button_events, *self.scroll_events),
                key=event_sort_key,
            )
        )

    @property
    def sparse_event_count(self) -> int:
        return len(self.keyboard_events) + len(self.mouse_button_events) + len(self.scroll_events)

    @property
    def has_mouse_motion(self) -> bool:
        return self.mouse_dx != 0 or self.mouse_dy != 0


@dataclass(frozen=True, slots=True)
class ScreenStateBin:
    """Optional latest-known screen state aligned to an action bin."""

    index: int
    start_ns: int
    end_ns: int
    screen_events: tuple[ScreenEvent, ...] = ()
    latest_cursor_position: tuple[float, float] | None = None
    latest_active_window: str | None = None


@dataclass(frozen=True, slots=True)
class VideoTimestep:
    """One visual timestep aligned to an action bin.

    ``source_span_*`` records the source frame timestamps included in the
    timestep. A causal-safe timestep has no source frame timestamp after
    ``decision_time_ns``.
    """

    action_bin_index: int
    action_start_ns: int
    action_end_ns: int
    policy: VideoSamplingPolicy
    source_frame_indices: tuple[int, ...]
    source_frame_timestamps_ns: tuple[int, ...]
    source_span_start_ns: int | None
    source_span_end_ns: int | None
    decision_time_ns: int
    causal_safe: bool
    source_fps: int = D2E_VIDEO_FPS
    metadata: dict[str, Any] | None = None

    @property
    def has_visual(self) -> bool:
        return bool(self.source_frame_indices)


@dataclass(frozen=True, slots=True)
class OWAMcapMessage:
    """Dependency-light raw MCAP message wrapper from the optional adapter."""

    topic: str
    log_time_ns: int
    publish_time_ns: int | None
    schema_name: str | None
    data: bytes


@dataclass(frozen=True, slots=True)
class BinningResult:
    """Result of assigning canonical events to non-overlapping action bins."""

    bins: tuple[ActionBin, ...]
    dropped_events: tuple[DroppedEvent, ...] = ()
    start_ns: int = 0
    stop_ns: int = 0
    bin_width_ns: int = DEFAULT_BIN_WIDTH_NS

    @property
    def dropped_event_count(self) -> int:
        return len(self.dropped_events)


_EVENT_FAMILY_ORDER: dict[EventFamily, int] = {
    EventFamily.KEYBOARD: 0,
    EventFamily.MOUSE_BUTTON: 1,
    EventFamily.SCROLL: 2,
    EventFamily.SCREEN: 3,
    EventFamily.MOUSE_MOVE: 4,
}


def event_sort_key(event: TimestampedEvent) -> tuple[int, int, str, str]:
    """Return a deterministic sort key for sparse canonical events."""

    family = event.family
    secondary = ""
    tertiary = ""
    if isinstance(event, KeyboardEvent):
        secondary = event.key
        tertiary = event.event_type.value
    elif isinstance(event, MouseButtonEvent):
        secondary = event.button.value
        tertiary = event.event_type.value
    elif isinstance(event, ScrollEvent):
        secondary = ",".join(direction.value for direction in event.directions)
        tertiary = f"{event.delta_x}:{event.delta_y}"
    elif isinstance(event, ScreenEvent):
        secondary = event.event_type.value
        tertiary = repr(event.value)
    return (event.timestamp_ns, _EVENT_FAMILY_ORDER[family], secondary, tertiary)


def _relative_to_or_self(path: Path, root: Path | None) -> Path:
    if root is None:
        return path
    try:
        return path.relative_to(root)
    except ValueError:
        return path
