"""Official-OWA writer round-trip support for bounded D2E evaluator smokes.

The default package remains dependency-light.  This module imports
``mcap_owa``/``owa.msgs`` only when a caller explicitly generates a real MCAP.
Offline tests can inject tiny fake reader/writer classes and never import the
optional packages.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from importlib import import_module
import os
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

from fdm_1_with_d2e.data.manifests import assert_artifact_path_outside_dataset_root, write_json_artifact
from fdm_1_with_d2e.data.mcap_json import (
    DecodedMcapJsonActions,
    bin_decoded_mcap_json_actions,
    read_d2e_json_mcap_actions,
)
from fdm_1_with_d2e.data.types import (
    ActionBin,
    KeyboardEvent,
    KeyboardEventType,
    MouseButtonEvent,
    MouseButtonEventType,
    MouseMoveEvent,
    ScrollEvent,
)
from fdm_1_with_d2e.evaluation.roundtrip import action_bin_to_canonical_events
from fdm_1_with_d2e.tokenization.actions import DEFAULT_ACTION_TOKENIZER, tokenize_action_bins

JSONDict = dict[str, Any]
OfficialRoundTripActionMode = Literal["exact", "tokenized"]

OFFICIAL_ROUNDTRIP_STORY_ID = "G015-run-writer-produced-mcap-official-roundtrip"
OFFICIAL_ROUNDTRIP_GENERATED_BY = "fdm_1_with_d2e.evaluation.official_roundtrip:v1"
OFFICIAL_ROUNDTRIP_PROVENANCE_SCHEMA = "fdm_1_with_d2e.official_roundtrip_prediction_provenance.v1"
OFFICIAL_ROUNDTRIP_ACTION_MODES: tuple[str, ...] = ("exact", "tokenized")
OFFICIAL_ROUNDTRIP_REQUIRED_TOPICS: tuple[str, ...] = ("screen", "keyboard", "mouse/raw")
OFFICIAL_ROUNDTRIP_MODULES: tuple[str, ...] = (
    "mcap_owa.highlevel",
    "owa.msgs.desktop.keyboard",
    "owa.msgs.desktop.mouse",
)
_CHUNK_SIZE = 1024 * 1024


class OptionalOfficialMcapDependencyError(ImportError):
    """Raised when official OWA writer/reader packages are unavailable."""

    def __init__(self, missing_modules: tuple[str, ...]) -> None:
        missing = ", ".join(missing_modules)
        super().__init__(
            "Official D2E writer round-trip generation requires optional OWA/MCAP "
            f"runtime packages that are not installed: {missing}. Run this on MLXP "
            "with the pinned D2E/OWA dependencies used by official evaluate.py "
            "(mcap-owa-support, owa-core, and owa-msgs). Offline tests do not "
            "require these packages."
        )
        self.missing_modules = missing_modules


@dataclass(frozen=True, slots=True)
class OfficialRoundTripDependencies:
    """Runtime classes needed to read source MCAPs and write prediction MCAPs."""

    OWAMcapReader: type[Any]
    OWAMcapWriter: type[Any]
    KeyboardEvent: type[Any]
    RawMouseEvent: type[Any]


@dataclass(frozen=True, slots=True)
class _PendingOwaWrite:
    timestamp_ns: int
    topic: str
    message: Any
    source: str


def require_official_roundtrip_dependencies(
    *,
    importer: Callable[[str], ModuleType] = import_module,
) -> OfficialRoundTripDependencies:
    """Import the optional OWA writer stack or raise a clear dependency error."""

    loaded: dict[str, ModuleType] = {}
    missing: list[str] = []
    for module_name in OFFICIAL_ROUNDTRIP_MODULES:
        try:
            loaded[module_name] = importer(module_name)
        except ImportError:
            missing.append(module_name)
    if missing:
        raise OptionalOfficialMcapDependencyError(tuple(missing))

    highlevel = loaded["mcap_owa.highlevel"]
    keyboard = loaded["owa.msgs.desktop.keyboard"]
    mouse = loaded["owa.msgs.desktop.mouse"]
    return OfficialRoundTripDependencies(
        OWAMcapReader=getattr(highlevel, "OWAMcapReader"),
        OWAMcapWriter=getattr(highlevel, "OWAMcapWriter"),
        KeyboardEvent=getattr(keyboard, "KeyboardEvent"),
        RawMouseEvent=getattr(mouse, "RawMouseEvent"),
    )


def generate_writer_roundtrip_prediction_mcap(
    source_mcap_path: str | Path,
    prediction_mcap_path: str | Path,
    *,
    action_mode: OfficialRoundTripActionMode = "exact",
    provenance_json_path: str | Path | None = None,
    dataset_root: str | Path | None = None,
    max_duration_seconds: float | None = None,
    overwrite: bool = False,
    generated_by: str = OFFICIAL_ROUNDTRIP_GENERATED_BY,
    dependencies: OfficialRoundTripDependencies | None = None,
    action_reader: Callable[[str | Path], DecodedMcapJsonActions] = read_d2e_json_mcap_actions,
) -> JSONDict:
    """Generate a prediction MCAP from a real D2E source MCAP through OWA writer APIs.

    The output is intentionally *not* a byte-copy of the ground-truth MCAP: it is
    read with ``OWAMcapReader``, re-emitted with ``OWAMcapWriter``, includes
    writer metadata, and returns/writes provenance with source/output hash and
    size checks. ``action_mode="exact"`` re-emits decoded official OWA action
    messages for schema sanity. ``action_mode="tokenized"`` copies screen events
    but routes actions through this repo's JSON-MCAP decoder, 50ms binner,
    tokenizer, de-tokenizer, and official OWA message constructors.
    """

    resolved_action_mode = _validate_action_mode(action_mode)
    source_path = Path(source_mcap_path)
    prediction_path = Path(prediction_mcap_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"source MCAP not found: {source_path}")
    if prediction_path.exists() and not overwrite:
        raise FileExistsError(f"prediction MCAP already exists; pass overwrite=True: {prediction_path}")

    assert_artifact_path_outside_dataset_root(prediction_path, dataset_root)
    if provenance_json_path is not None:
        assert_artifact_path_outside_dataset_root(provenance_json_path, dataset_root)

    deps = dependencies or require_official_roundtrip_dependencies()
    max_duration_ns = _duration_seconds_to_ns(max_duration_seconds)
    source_hash = _file_sha256(source_path)
    source_size = source_path.stat().st_size
    first_screen = _read_first_screen_info(deps, source_path)
    start_timestamp_ns = int(first_screen["mcap_timestamp_ns"])
    stop_timestamp_ns = None if max_duration_ns is None else start_timestamp_ns + max_duration_ns

    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = _temporary_output_path(prediction_path)
    if tmp_path.exists():
        tmp_path.unlink()

    topic_counts: Counter[str] = Counter()
    try:
        with deps.OWAMcapReader(source_path) as reader, deps.OWAMcapWriter(tmp_path) as writer:
            _write_writer_metadata(
                writer,
                {
                    "story_id": OFFICIAL_ROUNDTRIP_STORY_ID,
                    "generated_by": generated_by,
                    "action_mode": resolved_action_mode,
                    "source_mcap_path": str(source_path),
                    "source_mcap_sha256": source_hash,
                    "source_mcap_size_bytes": str(source_size),
                    "first_screen_mcap_timestamp_ns": str(start_timestamp_ns),
                    "first_screen_pts_ns": str(first_screen["pts_ns"]),
                    "max_duration_ns": "" if max_duration_ns is None else str(max_duration_ns),
                },
            )
            if resolved_action_mode == "exact":
                action_summary = _write_exact_roundtrip_messages(
                    reader,
                    writer,
                    source_path=source_path,
                    dependencies=deps,
                    start_timestamp_ns=start_timestamp_ns,
                    stop_timestamp_ns=stop_timestamp_ns,
                    topic_counts=topic_counts,
                )
            else:
                action_summary = _write_tokenized_roundtrip_messages(
                    reader,
                    writer,
                    source_path=source_path,
                    dependencies=deps,
                    action_reader=action_reader,
                    start_timestamp_ns=start_timestamp_ns,
                    stop_timestamp_ns=stop_timestamp_ns,
                    topic_counts=topic_counts,
                )
        _validate_required_topic_counts(topic_counts)
        os.replace(tmp_path, prediction_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise

    prediction_hash = _file_sha256(prediction_path)
    prediction_size = prediction_path.stat().st_size
    if prediction_hash == source_hash:
        prediction_path.unlink(missing_ok=True)
        raise RuntimeError(
            "writer-produced prediction MCAP is byte-identical to source; "
            "cannot prove it was generated rather than copied"
        )

    provenance = {
        "schema": OFFICIAL_ROUNDTRIP_PROVENANCE_SCHEMA,
        "story_id": OFFICIAL_ROUNDTRIP_STORY_ID,
        "generated_by": generated_by,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "action_mode": resolved_action_mode,
        "source": {
            "path": str(source_path),
            "sha256": source_hash,
            "size_bytes": source_size,
        },
        "prediction": {
            "path": str(prediction_path),
            "sha256": prediction_hash,
            "size_bytes": prediction_size,
        },
        "not_copied_proof": {
            "writer_generated": True,
            "source_sha256_equals_prediction_sha256": source_hash == prediction_hash,
            "source_size_equals_prediction_size": source_size == prediction_size,
            "writer_metadata_name": "fdm_1_with_d2e.roundtrip_provenance",
        },
        "topics_written": _sorted_count_dict(topic_counts),
        "events_written": _sorted_count_dict(action_summary["events_written"]),
        "tokenized_bin_count": action_summary["tokenized_bin_count"],
        "tokenized_overflow_bin_count": action_summary["tokenized_overflow_bin_count"],
        "tokenized_overflow_bin_fraction": action_summary["tokenized_overflow_bin_fraction"],
        "decoded_counts": action_summary["decoded_counts"],
        "skipped_scroll_count": action_summary["skipped_scroll_count"],
        "tokenized_action_summary": action_summary["tokenized_action_summary"],
        "required_topics": list(OFFICIAL_ROUNDTRIP_REQUIRED_TOPICS),
        "first_screen": first_screen,
        "time_filter": {
            "start_mcap_timestamp_ns": start_timestamp_ns,
            "stop_mcap_timestamp_ns": stop_timestamp_ns,
            "max_duration_ns": max_duration_ns,
        },
        "official_evaluate_compatibility": {
            "pinned_evaluate_topics": list(OFFICIAL_ROUNDTRIP_REQUIRED_TOPICS),
            "alignment": "first screen event media_ref.pts_ns with event.timestamp offset, matching pinned evaluate.py",
            "writer_api": "mcap_owa.highlevel.OWAMcapWriter.write_message(message, topic=..., timestamp=...)",
        },
    }
    if provenance_json_path is not None:
        write_json_artifact(provenance, provenance_json_path, dataset_root=dataset_root)
    return provenance


def default_provenance_json_path(prediction_mcap_path: str | Path) -> Path:
    """Return the default sidecar path for a generated prediction MCAP."""

    return Path(f"{prediction_mcap_path}.provenance.json")


def file_provenance(path: str | Path) -> JSONDict:
    """Return hash/size provenance for an existing file."""

    file_path = Path(path)
    return {
        "path": str(file_path),
        "sha256": _file_sha256(file_path),
        "size_bytes": file_path.stat().st_size,
    }


def _validate_action_mode(action_mode: str) -> OfficialRoundTripActionMode:
    if action_mode not in OFFICIAL_ROUNDTRIP_ACTION_MODES:
        raise ValueError(f"action_mode must be one of {OFFICIAL_ROUNDTRIP_ACTION_MODES}, got {action_mode!r}")
    return action_mode  # type: ignore[return-value]


def _write_exact_roundtrip_messages(
    reader: Any,
    writer: Any,
    *,
    source_path: Path,
    dependencies: OfficialRoundTripDependencies,
    start_timestamp_ns: int,
    stop_timestamp_ns: int | None,
    topic_counts: Counter[str],
) -> JSONDict:
    event_counts: Counter[str] = Counter()
    for mcap_msg in reader.iter_messages(topics=list(OFFICIAL_ROUNDTRIP_REQUIRED_TOPICS)):
        timestamp_ns = _message_timestamp_ns(mcap_msg)
        if timestamp_ns < start_timestamp_ns:
            continue
        if stop_timestamp_ns is not None and timestamp_ns > stop_timestamp_ns:
            # OWAMcapReader yields messages in log-time order; the pinned
            # evaluator's own binning loop depends on the same ordering.
            break
        topic = str(getattr(mcap_msg, "topic"))
        _write_reconstructed_message(writer, mcap_msg, source_path=source_path, dependencies=dependencies)
        topic_counts[topic] += 1
        event_counts[_exact_event_count_key(topic)] += 1
    return _action_summary(
        event_counts,
        tokenized_bin_count=None,
        tokenized_overflow_bin_count=None,
        tokenized_overflow_bin_fraction=None,
        decoded_counts=None,
        skipped_scroll_count=0,
        tokenized_action_summary=None,
    )


def _write_tokenized_roundtrip_messages(
    reader: Any,
    writer: Any,
    *,
    source_path: Path,
    dependencies: OfficialRoundTripDependencies,
    action_reader: Callable[[str | Path], DecodedMcapJsonActions],
    start_timestamp_ns: int,
    stop_timestamp_ns: int | None,
    topic_counts: Counter[str],
) -> JSONDict:
    event_counts: Counter[str] = Counter()
    pending_writes: list[_PendingOwaWrite] = []

    for mcap_msg in reader.iter_messages(topics=["screen"]):
        timestamp_ns = _message_timestamp_ns(mcap_msg)
        if timestamp_ns < start_timestamp_ns:
            continue
        if stop_timestamp_ns is not None and timestamp_ns > stop_timestamp_ns:
            break
        pending_writes.append(
            _PendingOwaWrite(
                timestamp_ns=timestamp_ns,
                topic="screen",
                message=_resolved_screen_message(getattr(mcap_msg, "decoded"), source_path),
                source="screen_exact_reemit",
            )
        )

    decoded = action_reader(source_path)
    binned = bin_decoded_mcap_json_actions(
        decoded,
        start_ns=start_timestamp_ns,
        stop_ns=stop_timestamp_ns,
        include_screen_span=True,
    )
    tokenized = tokenize_action_bins(binned.bins, tokenizer=DEFAULT_ACTION_TOKENIZER)
    reconstructed_bins = DEFAULT_ACTION_TOKENIZER.detokenize_bins(tokenized)
    action_writes, skipped_scroll_count = _pending_tokenized_action_writes(
        reconstructed_bins,
        dependencies=dependencies,
        start_timestamp_ns=start_timestamp_ns,
        stop_timestamp_ns=stop_timestamp_ns,
    )
    pending_writes.extend(action_writes)

    for pending in sorted(pending_writes, key=_pending_write_sort_key):
        writer.write_message(pending.message, topic=pending.topic, timestamp=pending.timestamp_ns)
        topic_counts[pending.topic] += 1
        event_counts[pending.source] += 1

    decoded_summary = decoded.to_json_summary()
    tokenized_summary = {
        "decoded_summary": decoded_summary,
        "binning": {
            "bin_count": len(binned.bins),
            "dropped_event_count": binned.dropped_event_count,
            "start_ns": binned.start_ns,
            "stop_ns": binned.stop_ns,
            "bin_width_ns": binned.bin_width_ns,
        },
        "tokenizer": {
            "tokens_per_bin": DEFAULT_ACTION_TOKENIZER.tokens_per_bin,
            "slots_per_bin": DEFAULT_ACTION_TOKENIZER.slots_per_bin,
            "token_count": len(tokenized.tokens),
            "overflow_bin_count": tokenized.overflow_bin_count,
            "overflow_bin_fraction": tokenized.overflow_bin_fraction,
        },
        "reconstructed_bin_count": len(reconstructed_bins),
        "skipped_scroll_count": skipped_scroll_count,
    }
    return _action_summary(
        event_counts,
        tokenized_bin_count=len(tokenized.bins),
        tokenized_overflow_bin_count=tokenized.overflow_bin_count,
        tokenized_overflow_bin_fraction=tokenized.overflow_bin_fraction,
        decoded_counts=decoded_summary["decoded_event_counts"],
        skipped_scroll_count=skipped_scroll_count,
        tokenized_action_summary=tokenized_summary,
    )


def _pending_tokenized_action_writes(
    action_bins: tuple[ActionBin, ...],
    *,
    dependencies: OfficialRoundTripDependencies,
    start_timestamp_ns: int,
    stop_timestamp_ns: int | None,
) -> tuple[list[_PendingOwaWrite], int]:
    pending: list[_PendingOwaWrite] = []
    skipped_scroll_count = 0
    for action_bin in action_bins:
        for event in action_bin_to_canonical_events(action_bin, include_zero_mouse=False):
            if not _timestamp_in_range(event.timestamp_ns, start_timestamp_ns, stop_timestamp_ns):
                continue
            if isinstance(event, KeyboardEvent):
                pending.append(
                    _PendingOwaWrite(
                        timestamp_ns=event.timestamp_ns,
                        topic="keyboard",
                        message=_canonical_keyboard_message(event, dependencies.KeyboardEvent),
                        source="keyboard_tokenized",
                    )
                )
            elif isinstance(event, MouseMoveEvent):
                pending.append(
                    _PendingOwaWrite(
                        timestamp_ns=event.timestamp_ns,
                        topic="mouse/raw",
                        message=_canonical_mouse_move_message(event, dependencies.RawMouseEvent),
                        source="mouse_move_tokenized",
                    )
                )
            elif isinstance(event, MouseButtonEvent):
                pending.append(
                    _PendingOwaWrite(
                        timestamp_ns=event.timestamp_ns,
                        topic="mouse/raw",
                        message=_canonical_mouse_button_message(event, dependencies.RawMouseEvent),
                        source="mouse_button_tokenized",
                    )
                )
            elif isinstance(event, ScrollEvent):
                skipped_scroll_count += 1
            else:  # pragma: no cover - defensive for future canonical event variants.
                raise TypeError(f"unsupported tokenized canonical event: {type(event)!r}")
    return pending, skipped_scroll_count


def _action_summary(
    events_written: Counter[str],
    *,
    tokenized_bin_count: int | None,
    tokenized_overflow_bin_count: int | None,
    tokenized_overflow_bin_fraction: float | None,
    decoded_counts: Mapping[str, int] | None,
    skipped_scroll_count: int,
    tokenized_action_summary: JSONDict | None,
) -> JSONDict:
    return {
        "events_written": dict(events_written),
        "tokenized_bin_count": tokenized_bin_count,
        "tokenized_overflow_bin_count": tokenized_overflow_bin_count,
        "tokenized_overflow_bin_fraction": tokenized_overflow_bin_fraction,
        "decoded_counts": dict(decoded_counts) if decoded_counts is not None else None,
        "skipped_scroll_count": skipped_scroll_count,
        "tokenized_action_summary": tokenized_action_summary,
    }


def _read_first_screen_info(deps: OfficialRoundTripDependencies, source_path: Path) -> JSONDict:
    with deps.OWAMcapReader(source_path) as reader:
        for mcap_msg in reader.iter_messages(topics=["screen"]):
            timestamp_ns = _message_timestamp_ns(mcap_msg)
            decoded = getattr(mcap_msg, "decoded")
            media_ref = _required_field(decoded, "media_ref", topic="screen")
            pts_ns = _required_field(media_ref, "pts_ns", topic="screen.media_ref")
            return {
                "mcap_timestamp_ns": timestamp_ns,
                "pts_ns": int(pts_ns),
            }
    raise ValueError("source MCAP has no screen events; official evaluate.py requires at least one screen event")


def _write_writer_metadata(writer: Any, data: Mapping[str, str]) -> None:
    write_metadata = getattr(writer, "write_metadata", None)
    if write_metadata is not None:
        write_metadata("fdm_1_with_d2e.roundtrip_provenance", {key: str(value) for key, value in data.items()})


def _write_reconstructed_message(
    writer: Any,
    mcap_msg: Any,
    *,
    source_path: Path,
    dependencies: OfficialRoundTripDependencies,
) -> None:
    topic = str(getattr(mcap_msg, "topic"))
    timestamp_ns = _message_timestamp_ns(mcap_msg)
    decoded = getattr(mcap_msg, "decoded")
    if topic == "screen":
        screen_msg = _resolved_screen_message(decoded, source_path)
        writer.write_message(screen_msg, topic="screen", timestamp=timestamp_ns)
    elif topic == "keyboard":
        writer.write_message(
            _keyboard_message(decoded, timestamp_ns, dependencies.KeyboardEvent),
            topic="keyboard",
            timestamp=timestamp_ns,
        )
    elif topic == "mouse/raw":
        writer.write_message(
            _raw_mouse_message(decoded, timestamp_ns, dependencies.RawMouseEvent),
            topic="mouse/raw",
            timestamp=timestamp_ns,
        )
    else:  # pragma: no cover - guarded by caller topic list.
        raise ValueError(f"unsupported topic for official round-trip writer: {topic!r}")


def _resolved_screen_message(decoded: Any, source_path: Path) -> Any:
    media_ref = _required_field(decoded, "media_ref", topic="screen")
    if _optional_field(media_ref, "pts_ns") is None:
        raise ValueError("screen media_ref missing pts_ns; official evaluate.py alignment would fail")
    resolve_relative_path = getattr(decoded, "resolve_relative_path", None)
    if resolve_relative_path is not None:
        return resolve_relative_path(str(source_path))
    return decoded


def _keyboard_message(decoded: Any, timestamp_ns: int, KeyboardEvent: type[Any]) -> Any:
    return KeyboardEvent(
        event_type=_string_value(_required_field(decoded, "event_type", topic="keyboard")),
        vk=int(_required_field(decoded, "vk", topic="keyboard")),
        timestamp=timestamp_ns,
    )


def _raw_mouse_message(decoded: Any, timestamp_ns: int, RawMouseEvent: type[Any]) -> Any:
    us_flags = _optional_field(
        decoded,
        "us_flags",
        default=_nested_constant(RawMouseEvent, "UsFlags", "MOUSE_MOVE_RELATIVE"),
    )
    button_flags = _optional_field(
        decoded,
        "button_flags",
        default=_nested_constant(RawMouseEvent, "ButtonFlags", "RI_MOUSE_NOP"),
    )
    return RawMouseEvent(
        last_x=int(_required_axis(decoded, "x")),
        last_y=int(_required_axis(decoded, "y")),
        us_flags=us_flags,
        button_flags=button_flags,
        button_data=int(_optional_field(decoded, "button_data", default=0)),
        device_handle=_optional_field(decoded, "device_handle"),
        timestamp=timestamp_ns,
    )


def _canonical_keyboard_message(event: KeyboardEvent, KeyboardEventClass: type[Any]) -> Any:
    return KeyboardEventClass(
        event_type=_keyboard_event_type_for_owa(event.event_type),
        vk=_vk_from_canonical_key(event.key),
        timestamp=event.timestamp_ns,
    )


def _canonical_mouse_move_message(event: MouseMoveEvent, RawMouseEvent: type[Any]) -> Any:
    return RawMouseEvent(
        last_x=int(event.dx),
        last_y=int(event.dy),
        us_flags=_nested_constant(RawMouseEvent, "UsFlags", "MOUSE_MOVE_RELATIVE"),
        button_flags=_nested_constant(RawMouseEvent, "ButtonFlags", "RI_MOUSE_NOP"),
        button_data=0,
        device_handle=None,
        timestamp=event.timestamp_ns,
    )


def _canonical_mouse_button_message(event: MouseButtonEvent, RawMouseEvent: type[Any]) -> Any:
    return RawMouseEvent(
        last_x=0,
        last_y=0,
        us_flags=_nested_constant(RawMouseEvent, "UsFlags", "MOUSE_MOVE_RELATIVE"),
        button_flags=_button_flag_for_event(event, RawMouseEvent),
        button_data=0,
        device_handle=None,
        timestamp=event.timestamp_ns,
    )


def _keyboard_event_type_for_owa(event_type: KeyboardEventType) -> str:
    value = event_type.value
    if value == "down":
        return "press"
    if value == "up":
        return "release"
    raise ValueError(f"unsupported canonical keyboard event type for OWA: {event_type!r}")


def _vk_from_canonical_key(key: str) -> int:
    if not key.startswith("VK_"):
        raise ValueError(
            "tokenized official writer only supports canonical keyboard keys in VK_<int> form; "
            f"got {key!r}"
        )
    try:
        return int(key[3:])
    except ValueError as exc:
        raise ValueError(f"canonical keyboard key must be VK_<int>, got {key!r}") from exc


def _button_flag_for_event(event: MouseButtonEvent, RawMouseEvent: type[Any]) -> Any:
    button = event.button.value.upper()
    transition = _mouse_button_transition_for_owa(event.event_type)
    flag_name = f"RI_MOUSE_{button}_BUTTON_{transition}"
    flag = _nested_constant(RawMouseEvent, "ButtonFlags", flag_name)
    if flag is None:
        raise ValueError(f"RawMouseEvent.ButtonFlags missing required official flag {flag_name!r}")
    return flag


def _mouse_button_transition_for_owa(event_type: MouseButtonEventType) -> str:
    value = event_type.value
    if value == "down":
        return "DOWN"
    if value == "up":
        return "UP"
    raise ValueError(f"unsupported canonical mouse button event type for OWA: {event_type!r}")


def _required_axis(decoded: Any, axis: str) -> Any:
    primary = f"last_{axis}"
    value = _optional_field(decoded, primary)
    if value is not None:
        return value
    fallback = f"d{axis}"
    value = _optional_field(decoded, fallback)
    if value is not None:
        return value
    raise ValueError(f"mouse/raw event missing {primary} or {fallback}")


def _validate_required_topic_counts(topic_counts: Mapping[str, int]) -> None:
    missing = [topic for topic in OFFICIAL_ROUNDTRIP_REQUIRED_TOPICS if int(topic_counts.get(topic, 0)) == 0]
    if missing:
        raise ValueError(
            "writer round-trip did not emit messages for required official evaluate.py topics: "
            f"{missing}; counts={_sorted_count_dict(topic_counts)}"
        )


def _message_timestamp_ns(mcap_msg: Any) -> int:
    if isinstance(mcap_msg, Mapping):
        return int(mcap_msg["timestamp"])
    return int(getattr(mcap_msg, "timestamp"))


def _timestamp_in_range(timestamp_ns: int, start_timestamp_ns: int, stop_timestamp_ns: int | None) -> bool:
    if timestamp_ns < start_timestamp_ns:
        return False
    return stop_timestamp_ns is None or timestamp_ns <= stop_timestamp_ns


def _pending_write_sort_key(pending: _PendingOwaWrite) -> tuple[int, int, str]:
    return (pending.timestamp_ns, _topic_write_order(pending.topic), pending.source)


def _topic_write_order(topic: str) -> int:
    try:
        return OFFICIAL_ROUNDTRIP_REQUIRED_TOPICS.index(topic)
    except ValueError:
        return len(OFFICIAL_ROUNDTRIP_REQUIRED_TOPICS)


def _exact_event_count_key(topic: str) -> str:
    if topic == "mouse/raw":
        return "mouse_raw_exact_reemit"
    return f"{topic}_exact_reemit"


def _required_field(obj: Any, field_name: str, *, topic: str) -> Any:
    value = _optional_field(obj, field_name)
    if value is None:
        raise ValueError(f"{topic} message missing required field {field_name!r}")
    return value


def _optional_field(obj: Any, field_name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(field_name, default)
    return getattr(obj, field_name, default)


def _string_value(value: Any) -> str:
    enum_value = getattr(value, "value", value)
    return str(enum_value)


def _nested_constant(cls: type[Any], nested_class_name: str, constant_name: str) -> Any:
    nested = getattr(cls, nested_class_name, None)
    if nested is None:
        return None
    return getattr(nested, constant_name, None)


def _duration_seconds_to_ns(seconds: float | None) -> int | None:
    if seconds is None:
        return None
    value = float(seconds)
    if value <= 0:
        raise ValueError("max_duration_seconds must be positive when provided")
    return int(value * 1_000_000_000)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _temporary_output_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.tmp")


def _sorted_count_dict(counts: Mapping[str, int]) -> dict[str, int]:
    return {key: int(counts[key]) for key in sorted(counts, key=str.casefold)}


__all__ = [
    "OFFICIAL_ROUNDTRIP_ACTION_MODES",
    "OFFICIAL_ROUNDTRIP_GENERATED_BY",
    "OFFICIAL_ROUNDTRIP_MODULES",
    "OFFICIAL_ROUNDTRIP_PROVENANCE_SCHEMA",
    "OFFICIAL_ROUNDTRIP_REQUIRED_TOPICS",
    "OFFICIAL_ROUNDTRIP_STORY_ID",
    "OfficialRoundTripDependencies",
    "OptionalOfficialMcapDependencyError",
    "default_provenance_json_path",
    "file_provenance",
    "generate_writer_roundtrip_prediction_mcap",
    "require_official_roundtrip_dependencies",
]
