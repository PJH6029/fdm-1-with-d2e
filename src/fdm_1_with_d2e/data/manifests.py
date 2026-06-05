"""Deterministic Phase 0 dataset, split, scale, and action manifests.

The builders in this module are intentionally dependency-light: they operate on
``D2ERecording`` references, canonical ``ActionBin`` objects, and tokenized bins
from the local tokenizer. Real D2E/MLXP runs can use the same functions after a
reader has produced the recording refs/bins, while the default tests remain fully
offline with synthetic fixtures.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from fdm_1_with_d2e.data.types import (
    DEFAULT_BIN_WIDTH_MS,
    DEFAULT_BIN_WIDTH_NS,
    NANOSECONDS_PER_SECOND,
    ActionBin,
    D2ERecording,
)
from fdm_1_with_d2e.tokenization.action_vocab import (
    EVENT_OVERFLOW,
    NO_ACTION,
    ActionTokenFamily,
)
from fdm_1_with_d2e.tokenization.actions import (
    DEFAULT_ACTION_TOKENIZER,
    ActionSlot,
    ActionTokenizer,
    OverflowRecord,
    TokenizedActionBin,
    TokenizedActionSequence,
)

MANIFEST_STORY_ID = "G004-implement-manifests-and-action-distr"
DATASET_MANIFEST_SCHEMA = "schemas/dataset_manifest.schema.json"
SPLIT_MANIFEST_SCHEMA = "schemas/split_manifest.schema.json"
SCALE_MANIFEST_SCHEMA = "schemas/scale_manifest.schema.json"
ACTION_DISTRIBUTION_SCHEMA = "schemas/action_distribution.schema.json"
DEFAULT_DATASET_NAME = "D2E-480p"
DEFAULT_SPLIT_SEED = 0
DEFAULT_SCALE_PERCENTAGES = (10, 50, 100)
OPTIONAL_SCALE_PERCENTAGES = (1, 5, 25)

JSONDict = dict[str, Any]
RecordingBinItems = Iterable[ActionBin | TokenizedActionBin | Sequence[str]] | TokenizedActionSequence
RecordingBins = Mapping[str, RecordingBinItems]
DurationMetadata = Mapping[str, int | float | Mapping[str, Any]]


class DatasetArtifactPathError(ValueError):
    """Raised when a generated artifact path points inside the read-only dataset."""


@dataclass(slots=True)
class _MouseMagnitudeStats:
    bin_count: int = 0
    nonzero_bin_count: int = 0
    abs_dx_sum: int = 0
    abs_dy_sum: int = 0
    l1_sum: int = 0
    l2_sum: float = 0.0
    max_abs_dx: int = 0
    max_abs_dy: int = 0
    max_l1: int = 0
    max_l2: float = 0.0

    def add(self, dx: int, dy: int) -> None:
        abs_dx = abs(int(dx))
        abs_dy = abs(int(dy))
        l1 = abs_dx + abs_dy
        l2 = math.hypot(abs_dx, abs_dy)
        self.bin_count += 1
        if abs_dx or abs_dy:
            self.nonzero_bin_count += 1
        self.abs_dx_sum += abs_dx
        self.abs_dy_sum += abs_dy
        self.l1_sum += l1
        self.l2_sum += l2
        self.max_abs_dx = max(self.max_abs_dx, abs_dx)
        self.max_abs_dy = max(self.max_abs_dy, abs_dy)
        self.max_l1 = max(self.max_l1, l1)
        self.max_l2 = max(self.max_l2, l2)

    def to_json(self) -> JSONDict:
        return {
            "bin_count": self.bin_count,
            "nonzero_bin_count": self.nonzero_bin_count,
            "nonzero_rate": _rate(self.nonzero_bin_count, self.bin_count),
            "abs_dx_sum": self.abs_dx_sum,
            "abs_dy_sum": self.abs_dy_sum,
            "l1_sum": self.l1_sum,
            "l2_sum": _round_float(self.l2_sum),
            "mean_abs_dx": _mean(self.abs_dx_sum, self.bin_count),
            "mean_abs_dy": _mean(self.abs_dy_sum, self.bin_count),
            "mean_l1": _mean(self.l1_sum, self.bin_count),
            "mean_l2": _mean(self.l2_sum, self.bin_count),
            "max_abs_dx": self.max_abs_dx,
            "max_abs_dy": self.max_abs_dy,
            "max_l1": self.max_l1,
            "max_l2": _round_float(self.max_l2),
        }


@dataclass(slots=True)
class _ActionDistributionStats:
    game: str
    recording_ids: set[str] = field(default_factory=set)
    bin_count: int = 0
    no_op_bin_count: int = 0
    event_count: int = 0
    event_family_counts: dict[str, int] = field(
        default_factory=lambda: {
            "mouse_move": 0,
            "keyboard": 0,
            "mouse_button": 0,
            "scroll": 0,
        }
    )
    token_family_counts: dict[str, int] = field(
        default_factory=lambda: {
            "mouse_move": 0,
            "keyboard": 0,
            "mouse_button": 0,
            "scroll": 0,
            "special": 0,
        }
    )
    overflow_bin_count: int = 0
    overflow_event_count: int = 0
    raw_mouse: _MouseMagnitudeStats = field(default_factory=_MouseMagnitudeStats)

    def add_canonical_bin(self, action_bin: ActionBin) -> None:
        keyboard_count = len(action_bin.keyboard_events)
        button_count = len(action_bin.mouse_button_events)
        scroll_count = sum(len(event.directions) for event in action_bin.scroll_events)
        has_mouse = action_bin.mouse_dx != 0 or action_bin.mouse_dy != 0
        event_count = (1 if has_mouse else 0) + keyboard_count + button_count + scroll_count

        self.bin_count += 1
        self.raw_mouse.add(action_bin.mouse_dx, action_bin.mouse_dy)
        if event_count == 0:
            self.no_op_bin_count += 1
        self.event_count += event_count
        if has_mouse:
            self.event_family_counts["mouse_move"] += 1
            self.token_family_counts["mouse_move"] += 1
        self.event_family_counts["keyboard"] += keyboard_count
        self.event_family_counts["mouse_button"] += button_count
        self.event_family_counts["scroll"] += scroll_count
        self.token_family_counts["keyboard"] += keyboard_count
        self.token_family_counts["mouse_button"] += button_count
        self.token_family_counts["scroll"] += scroll_count

    def add_tokenized_bin(
        self,
        tokenized_bin: TokenizedActionBin | Sequence[str],
        *,
        tokenizer: ActionTokenizer,
    ) -> None:
        if isinstance(tokenized_bin, TokenizedActionBin):
            tokens = tokenized_bin.tokens
            dx = tokenized_bin.original_mouse_dx
            dy = tokenized_bin.original_mouse_dy
            overflow = tokenized_bin.overflow
            event_slots: Sequence[ActionSlot | str] = tokenized_bin.event_slots
        else:
            tokens = tuple(tokenized_bin)
            if len(tokens) != tokenizer.tokens_per_bin:
                raise ValueError(
                    f"expected {tokenizer.tokens_per_bin} tokens per raw tokenized bin, got {len(tokens)}"
                )
            dx, dy = tokenizer.vocab.mouse_quantizer.dequantize_token(tokens[0])
            overflow = None
            event_slots = tokens[1:]

        event_count = 0
        overflow_marker = False
        self.bin_count += 1
        self.raw_mouse.add(dx, dy)
        has_mouse = dx != 0 or dy != 0
        if has_mouse:
            self.event_family_counts["mouse_move"] += 1
            self.token_family_counts["mouse_move"] += 1
            event_count += 1

        for slot in event_slots:
            token = slot.token if isinstance(slot, ActionSlot) else str(slot)
            if token == NO_ACTION:
                continue
            if token == EVENT_OVERFLOW:
                overflow_marker = True
                self.token_family_counts["special"] += 1
                continue
            family = tokenizer.vocab.token_family(token)
            if family is ActionTokenFamily.SPECIAL:
                self.token_family_counts["special"] += 1
                continue
            family_value = family.value
            self.event_family_counts[family_value] = self.event_family_counts.get(family_value, 0) + 1
            self.token_family_counts[family_value] = self.token_family_counts.get(family_value, 0) + 1
            event_count += 1

        if event_count == 0 and not overflow_marker:
            self.no_op_bin_count += 1
        self.event_count += event_count
        if overflow is not None or overflow_marker:
            self.overflow_bin_count += 1
            self.overflow_event_count += overflow.dropped_event_count if overflow is not None else 0

    def merge(self, other: "_ActionDistributionStats") -> None:
        self.recording_ids.update(other.recording_ids)
        self.bin_count += other.bin_count
        self.no_op_bin_count += other.no_op_bin_count
        self.event_count += other.event_count
        self.overflow_bin_count += other.overflow_bin_count
        self.overflow_event_count += other.overflow_event_count
        for key, value in other.event_family_counts.items():
            self.event_family_counts[key] = self.event_family_counts.get(key, 0) + value
        for key, value in other.token_family_counts.items():
            self.token_family_counts[key] = self.token_family_counts.get(key, 0) + value
        self.raw_mouse.bin_count += other.raw_mouse.bin_count
        self.raw_mouse.nonzero_bin_count += other.raw_mouse.nonzero_bin_count
        self.raw_mouse.abs_dx_sum += other.raw_mouse.abs_dx_sum
        self.raw_mouse.abs_dy_sum += other.raw_mouse.abs_dy_sum
        self.raw_mouse.l1_sum += other.raw_mouse.l1_sum
        self.raw_mouse.l2_sum += other.raw_mouse.l2_sum
        self.raw_mouse.max_abs_dx = max(self.raw_mouse.max_abs_dx, other.raw_mouse.max_abs_dx)
        self.raw_mouse.max_abs_dy = max(self.raw_mouse.max_abs_dy, other.raw_mouse.max_abs_dy)
        self.raw_mouse.max_l1 = max(self.raw_mouse.max_l1, other.raw_mouse.max_l1)
        self.raw_mouse.max_l2 = max(self.raw_mouse.max_l2, other.raw_mouse.max_l2)

    def to_json(self) -> JSONDict:
        active_bin_count = self.bin_count - self.no_op_bin_count
        return {
            "game": self.game,
            "recording_count": len(self.recording_ids),
            "recording_ids": sorted(self.recording_ids),
            "bin_count": self.bin_count,
            "active_action_bin_count": active_bin_count,
            "no_op_bin_count": self.no_op_bin_count,
            "no_op_rate": _rate(self.no_op_bin_count, self.bin_count),
            "event_count": self.event_count,
            "event_family_counts": _sorted_count_dict(self.event_family_counts),
            "token_family_counts": _sorted_count_dict(self.token_family_counts),
            "overflow_bin_count": self.overflow_bin_count,
            "overflow_event_count": self.overflow_event_count,
            "overflow_rate": _rate(self.overflow_bin_count, self.bin_count),
            "raw_mouse_magnitude_summary": self.raw_mouse.to_json(),
        }


def build_dataset_manifest(
    recordings: Iterable[D2ERecording],
    *,
    dataset_root: str | Path | None = None,
    dataset_name: str = DEFAULT_DATASET_NAME,
    include_checksums: bool = False,
    checksum_algorithm: str = "sha256",
    duration_metadata: DurationMetadata | None = None,
    timebase_ms: int = DEFAULT_BIN_WIDTH_MS,
    created_by_story: str = MANIFEST_STORY_ID,
) -> JSONDict:
    """Build a deterministic dataset manifest from discovered recording refs."""

    if timebase_ms <= 0:
        raise ValueError("timebase_ms must be positive")
    if include_checksums and checksum_algorithm != "sha256":
        raise ValueError("only sha256 checksums are supported")

    recording_refs = tuple(recordings)
    root = _resolve_dataset_root(recording_refs, dataset_root)
    entries = [
        _recording_manifest_entry(
            recording,
            dataset_root=root,
            include_checksums=include_checksums,
            checksum_algorithm=checksum_algorithm,
            duration_metadata=duration_metadata,
            bin_width_ns=timebase_ms * 1_000_000,
        )
        for recording in recording_refs
    ]
    entries.sort(key=_recording_entry_sort_key)
    payload: JSONDict = {
        "schema": DATASET_MANIFEST_SCHEMA,
        "manifest_id": "",
        "dataset_name": dataset_name,
        "dataset_root": _path_to_posix(root) if root is not None else None,
        "timebase_ms": timebase_ms,
        "recording_count": len(entries),
        "game_count": len({entry["game"] for entry in entries}),
        "games": sorted({entry["game"] for entry in entries}),
        "checksum_algorithm": checksum_algorithm if include_checksums else None,
        "recordings": entries,
        "created_by_story": created_by_story,
    }
    payload["manifest_id"] = stable_manifest_id("dataset", payload)
    return payload


def build_train_val_test_split_manifest(
    dataset_manifest: Mapping[str, Any],
    *,
    seed: int = DEFAULT_SPLIT_SEED,
    train_fraction: float = 0.8,
    validation_fraction: float = 0.1,
    test_fraction: float = 0.1,
    per_game: bool = True,
    created_by_story: str = MANIFEST_STORY_ID,
) -> JSONDict:
    """Build a deterministic train/validation/test split over recordings."""

    entries = _dataset_entries(dataset_manifest)
    return _build_split_manifest_for_entries(
        entries,
        source_dataset_manifest_id=str(dataset_manifest["manifest_id"]),
        seed=seed,
        train_fraction=train_fraction,
        validation_fraction=validation_fraction,
        test_fraction=test_fraction,
        per_game=per_game,
        held_out_games=(),
        held_out_test=(),
        split_policy=(
            "deterministic per-game train/validation/test split"
            if per_game
            else "deterministic global train/validation/test split"
        ),
        created_by_story=created_by_story,
    )


def build_held_out_game_split_manifest(
    dataset_manifest: Mapping[str, Any],
    held_out_games: Iterable[str],
    *,
    seed: int = DEFAULT_SPLIT_SEED,
    train_fraction: float = 0.8,
    validation_fraction: float = 0.1,
    test_fraction: float = 0.1,
    created_by_story: str = MANIFEST_STORY_ID,
) -> JSONDict:
    """Build a split where named games are excluded from training and held out."""

    entries = _dataset_entries(dataset_manifest)
    requested = tuple(sorted(dict.fromkeys(str(game) for game in held_out_games)))
    games = {str(entry["game"]) for entry in entries}
    missing = sorted(set(requested) - games)
    if missing:
        raise ValueError(f"held-out games not present in dataset manifest: {missing}")

    held_out_set = set(requested)
    in_game_entries = [entry for entry in entries if entry["game"] not in held_out_set]
    held_out_ids = tuple(
        sorted(
            (str(entry["recording_id"]) for entry in entries if entry["game"] in held_out_set),
            key=str.casefold,
        )
    )
    return _build_split_manifest_for_entries(
        in_game_entries,
        source_dataset_manifest_id=str(dataset_manifest["manifest_id"]),
        seed=seed,
        train_fraction=train_fraction,
        validation_fraction=validation_fraction,
        test_fraction=test_fraction,
        per_game=True,
        held_out_games=requested,
        held_out_test=held_out_ids,
        split_policy="deterministic in-game split with named held-out games excluded from train/validation/test",
        created_by_story=created_by_story,
    )


def build_scale_manifest(
    split_manifest: Mapping[str, Any],
    *,
    dataset_manifest: Mapping[str, Any] | None = None,
    percentages: Iterable[int] = DEFAULT_SCALE_PERCENTAGES,
    optional_percentages: Iterable[int] = (),
    seed: int = DEFAULT_SPLIT_SEED,
    source_split: str = "train",
    stratify_by_game: bool = True,
    created_by_story: str = MANIFEST_STORY_ID,
) -> JSONDict:
    """Build deterministic nested data-scale subsets from a split manifest."""

    requested_percentages = tuple(sorted({*percentages, *optional_percentages}))
    if not requested_percentages:
        raise ValueError("at least one scale percentage is required")
    for percentage in requested_percentages:
        if percentage <= 0 or percentage > 100:
            raise ValueError(f"scale percentage must be in (0, 100], got {percentage}")

    source_ids = tuple(str(item) for item in split_manifest.get(source_split, ()))
    game_by_id = _recording_game_map(dataset_manifest) if dataset_manifest is not None else {}
    scales: dict[str, list[str]] = {}
    for percentage in requested_percentages:
        if stratify_by_game and game_by_id:
            selected = _select_scale_ids_by_game(source_ids, game_by_id, percentage, seed)
        else:
            selected = _select_scale_ids(source_ids, percentage, seed, source_split)
        scales[_scale_key(percentage)] = selected

    payload: JSONDict = {
        "schema": SCALE_MANIFEST_SCHEMA,
        "manifest_id": "",
        "source_split_manifest_id": str(split_manifest["manifest_id"]),
        "source_dataset_manifest_id": dataset_manifest.get("manifest_id") if dataset_manifest is not None else None,
        "scale_policy": (
            f"deterministic nested {source_split} subsets; stratified by game when dataset_manifest is provided"
        ),
        "seed": seed,
        "source_split": source_split,
        "percentages": list(requested_percentages),
        "scales": scales,
        "scale_counts": {key: len(value) for key, value in scales.items()},
        "validation": list(split_manifest.get("validation", ())),
        "test": list(split_manifest.get("test", ())),
        "held_out_test": list(split_manifest.get("held_out_test", ())),
        "created_by_story": created_by_story,
    }
    payload["manifest_id"] = stable_manifest_id("scale", payload)
    return payload


def build_action_distribution_manifest(
    dataset_manifest: Mapping[str, Any],
    recording_bins: RecordingBins,
    *,
    tokenizer: ActionTokenizer = DEFAULT_ACTION_TOKENIZER,
    timebase_ms: int = DEFAULT_BIN_WIDTH_MS,
    created_by_story: str = MANIFEST_STORY_ID,
) -> JSONDict:
    """Summarize per-game action distributions from canonical or tokenized bins."""

    game_by_id = _recording_game_map(dataset_manifest)
    missing = sorted(set(recording_bins) - set(game_by_id))
    if missing:
        raise ValueError(f"recording_bins contains ids absent from dataset manifest: {missing}")

    per_game: dict[str, _ActionDistributionStats] = {}
    totals = _ActionDistributionStats(game="ALL")
    for recording_id in sorted(recording_bins, key=str.casefold):
        game = game_by_id[recording_id]
        stats = per_game.setdefault(game, _ActionDistributionStats(game=game))
        stats.recording_ids.add(recording_id)
        totals.recording_ids.add(recording_id)
        items = recording_bins[recording_id]
        iterable = items.bins if isinstance(items, TokenizedActionSequence) else items
        for item in iterable:
            if isinstance(item, ActionBin):
                stats.add_canonical_bin(item)
                totals.add_canonical_bin(item)
            else:
                stats.add_tokenized_bin(item, tokenizer=tokenizer)
                totals.add_tokenized_bin(item, tokenizer=tokenizer)

    summaries = [per_game[game].to_json() for game in sorted(per_game, key=str.casefold)]
    payload: JSONDict = {
        "schema": ACTION_DISTRIBUTION_SCHEMA,
        "manifest_id": "",
        "source_dataset_manifest_id": str(dataset_manifest["manifest_id"]),
        "timebase_ms": timebase_ms,
        "recording_count": len(recording_bins),
        "game_count": len(per_game),
        "summaries": summaries,
        "totals": totals.to_json(),
        "created_by_story": created_by_story,
    }
    payload["manifest_id"] = stable_manifest_id("action-distribution", payload)
    return payload


def assert_artifact_path_outside_dataset_root(
    output_path: str | Path,
    dataset_root: str | Path | None,
) -> None:
    """Reject output paths that would write inside the read-only D2E dataset."""

    if dataset_root is None:
        return
    output_resolved = Path(output_path).expanduser().resolve(strict=False)
    root_resolved = Path(dataset_root).expanduser().resolve(strict=False)
    if output_resolved == root_resolved or root_resolved in output_resolved.parents:
        raise DatasetArtifactPathError(
            f"refusing to write artifact inside read-only dataset root: output={output_resolved} root={root_resolved}"
        )


def stable_json_dumps(payload: Mapping[str, Any]) -> str:
    """Serialize JSON with stable key ordering and a trailing newline."""

    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_json_artifact(
    payload: Mapping[str, Any],
    output_path: str | Path,
    *,
    dataset_root: str | Path | None = None,
) -> Path:
    """Write a stable JSON artifact after applying the dataset write guard."""

    assert_artifact_path_outside_dataset_root(output_path, dataset_root)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stable_json_dumps(payload), encoding="utf-8")
    return path


def load_json(path: str | Path) -> JSONDict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def stable_manifest_id(kind: str, payload: Mapping[str, Any]) -> str:
    """Return a content-derived deterministic manifest id for a JSON payload."""

    canonical = dict(payload)
    canonical["manifest_id"] = ""
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
    return f"phase0-{kind}-{digest}"


def action_bin_from_mapping(mapping: Mapping[str, Any]) -> ActionBin:
    """Create an ``ActionBin`` from the dependency-light JSON fixture shape."""

    from fdm_1_with_d2e.data.types import (  # Local import avoids widening module import surface.
        KeyboardEvent,
        KeyboardEventType,
        MouseButton,
        MouseButtonEvent,
        MouseButtonEventType,
        ScrollEvent,
    )

    return ActionBin(
        index=int(mapping["index"]),
        start_ns=int(mapping["start_ns"]),
        end_ns=int(mapping["end_ns"]),
        mouse_dx=int(mapping.get("mouse_dx", 0)),
        mouse_dy=int(mapping.get("mouse_dy", 0)),
        keyboard_events=tuple(
            KeyboardEvent(
                timestamp_ns=int(event["timestamp_ns"]),
                key=str(event["key"]),
                event_type=KeyboardEventType(str(event["event_type"])),
            )
            for event in mapping.get("keyboard_events", ())
        ),
        mouse_button_events=tuple(
            MouseButtonEvent(
                timestamp_ns=int(event["timestamp_ns"]),
                button=MouseButton(str(event["button"])),
                event_type=MouseButtonEventType(str(event["event_type"])),
            )
            for event in mapping.get("mouse_button_events", ())
        ),
        scroll_events=tuple(
            ScrollEvent(
                timestamp_ns=int(event["timestamp_ns"]),
                delta_x=int(event.get("delta_x", 0)),
                delta_y=int(event.get("delta_y", 0)),
            )
            for event in mapping.get("scroll_events", ())
        ),
    )


def action_bins_from_jsonable(payload: Mapping[str, Any]) -> dict[str, tuple[ActionBin, ...]]:
    """Parse the fixture JSON shape consumed by ``summarize_action_distribution.py``."""

    raw_recording_bins = payload.get("recording_bins", payload)
    if not isinstance(raw_recording_bins, Mapping):
        raise ValueError("bins JSON must be a mapping or contain a 'recording_bins' mapping")
    return {
        str(recording_id): tuple(action_bin_from_mapping(item) for item in bins)
        for recording_id, bins in raw_recording_bins.items()
    }


def _recording_manifest_entry(
    recording: D2ERecording,
    *,
    dataset_root: Path | None,
    include_checksums: bool,
    checksum_algorithm: str,
    duration_metadata: DurationMetadata | None,
    bin_width_ns: int,
) -> JSONDict:
    video_path = Path(recording.video_path)
    mcap_path = Path(recording.mcap_path)
    duration_ns = _duration_ns_for_recording(recording, duration_metadata)
    duration_seconds = duration_ns / NANOSECONDS_PER_SECOND if duration_ns is not None else None
    timebase_bin_count = math.ceil(duration_ns / bin_width_ns) if duration_ns is not None else None
    video_size, video_checksum = _file_metadata(video_path, include_checksums, checksum_algorithm)
    mcap_size, mcap_checksum = _file_metadata(mcap_path, include_checksums, checksum_algorithm)
    return {
        "recording_id": recording.recording_id,
        "game": recording.game,
        "stem": recording.stem,
        "split": recording.split,
        "video_path": _path_to_posix(_relative_to_or_self(video_path, dataset_root)),
        "mcap_path": _path_to_posix(_relative_to_or_self(mcap_path, dataset_root)),
        "video_size_bytes": video_size,
        "mcap_size_bytes": mcap_size,
        "size_bytes_total": video_size + mcap_size,
        "video_sha256": video_checksum,
        "mcap_sha256": mcap_checksum,
        "duration_ns": duration_ns,
        "duration_seconds": _round_float(duration_seconds) if duration_seconds is not None else None,
        "timebase_bin_count": timebase_bin_count,
    }


def _file_metadata(path: Path, include_checksum: bool, checksum_algorithm: str) -> tuple[int, str | None]:
    size_bytes = path.stat().st_size
    if not include_checksum:
        return size_bytes, None
    digest = hashlib.new(checksum_algorithm)
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return size_bytes, digest.hexdigest()


def _duration_ns_for_recording(
    recording: D2ERecording,
    duration_metadata: DurationMetadata | None,
) -> int | None:
    if duration_metadata is not None and recording.recording_id in duration_metadata:
        value = duration_metadata[recording.recording_id]
        if isinstance(value, Mapping):
            if value.get("duration_ns") is not None:
                return int(value["duration_ns"])
            if value.get("duration_seconds") is not None:
                return int(round(float(value["duration_seconds"]) * NANOSECONDS_PER_SECOND))
        return int(value)
    return recording.duration_ns


def _resolve_dataset_root(recordings: Iterable[D2ERecording], dataset_root: str | Path | None) -> Path | None:
    if dataset_root is not None:
        return Path(dataset_root)
    roots = {recording.dataset_root for recording in recordings if recording.dataset_root is not None}
    if len(roots) == 1:
        return next(iter(roots))
    return None


def _build_split_manifest_for_entries(
    entries: Sequence[Mapping[str, Any]],
    *,
    source_dataset_manifest_id: str,
    seed: int,
    train_fraction: float,
    validation_fraction: float,
    test_fraction: float,
    per_game: bool,
    held_out_games: Sequence[str],
    held_out_test: Sequence[str],
    split_policy: str,
    created_by_story: str,
) -> JSONDict:
    _validate_split_fractions(train_fraction, validation_fraction, test_fraction)
    train: list[str] = []
    validation: list[str] = []
    test: list[str] = []
    per_game_counts: dict[str, dict[str, int]] = {}
    underfilled_games: list[str] = []

    groups: dict[str, list[str]] = defaultdict(list)
    if per_game:
        for entry in entries:
            groups[str(entry["game"])].append(str(entry["recording_id"]))
    else:
        groups["ALL"] = [str(entry["recording_id"]) for entry in entries]

    for game in sorted(groups, key=str.casefold):
        ids = groups[game]
        split = _split_ids(
            ids,
            seed=seed,
            salt=game,
            train_fraction=train_fraction,
            validation_fraction=validation_fraction,
            test_fraction=test_fraction,
        )
        train.extend(split["train"])
        validation.extend(split["validation"])
        test.extend(split["test"])
        if per_game and len(ids) < 3:
            underfilled_games.append(game)
        per_game_counts[game] = {key: len(value) for key, value in split.items()}

    payload: JSONDict = {
        "schema": SPLIT_MANIFEST_SCHEMA,
        "manifest_id": "",
        "source_dataset_manifest_id": source_dataset_manifest_id,
        "split_policy": split_policy,
        "seed": seed,
        "fractions": {
            "train": train_fraction,
            "validation": validation_fraction,
            "test": test_fraction,
        },
        "train": sorted(train, key=str.casefold),
        "validation": sorted(validation, key=str.casefold),
        "test": sorted(test, key=str.casefold),
        "held_out_games": list(held_out_games),
        "held_out_test": list(held_out_test),
        "counts": {
            "train": len(train),
            "validation": len(validation),
            "test": len(test),
            "held_out_test": len(held_out_test),
        },
        "per_game_counts": per_game_counts,
        "underfilled_games": sorted(underfilled_games, key=str.casefold),
        "created_by_story": created_by_story,
    }
    payload["manifest_id"] = stable_manifest_id("split", payload)
    return payload


def _split_ids(
    ids: Sequence[str],
    *,
    seed: int,
    salt: str,
    train_fraction: float,
    validation_fraction: float,
    test_fraction: float,
) -> dict[str, list[str]]:
    ordered = _stable_shuffle(ids, seed, salt)
    count = len(ordered)
    if count == 0:
        return {"train": [], "validation": [], "test": []}
    if count == 1:
        return {"train": ordered, "validation": [], "test": []}
    if count == 2:
        return {"train": ordered[:1], "validation": [], "test": ordered[1:]}

    validation_count = max(1, int(round(count * validation_fraction)))
    test_count = max(1, int(round(count * test_fraction)))
    while validation_count + test_count >= count:
        if validation_count >= test_count and validation_count > 1:
            validation_count -= 1
        elif test_count > 1:
            test_count -= 1
        else:
            break
    train_count = count - validation_count - test_count
    if train_count <= 0:  # Defensive; count >= 3 and reductions above should avoid this.
        train_count = 1
        if validation_count > test_count:
            validation_count -= 1
        else:
            test_count -= 1
    validation_start = train_count
    test_start = validation_start + validation_count
    return {
        "train": ordered[:train_count],
        "validation": ordered[validation_start:test_start],
        "test": ordered[test_start:],
    }


def _select_scale_ids(ids: Sequence[str], percentage: int, seed: int, salt: str) -> list[str]:
    ordered = _stable_shuffle(ids, seed, f"scale:{salt}")
    take = _scale_take_count(len(ordered), percentage)
    return sorted(ordered[:take], key=str.casefold)


def _select_scale_ids_by_game(
    ids: Sequence[str],
    game_by_id: Mapping[str, str],
    percentage: int,
    seed: int,
) -> list[str]:
    source = set(ids)
    groups: dict[str, list[str]] = defaultdict(list)
    for recording_id in ids:
        groups[game_by_id.get(recording_id, "")].append(recording_id)
    selected: list[str] = []
    for game in sorted(groups, key=str.casefold):
        ordered = _stable_shuffle(groups[game], seed, f"scale:{percentage}:{game}")
        take = _scale_take_count(len(ordered), percentage)
        selected.extend(ordered[:take])
    if percentage == 100:
        selected = list(source)
    return sorted(selected, key=lambda item: (game_by_id.get(item, "").casefold(), item.casefold()))


def _scale_take_count(total: int, percentage: int) -> int:
    if total == 0:
        return 0
    if percentage == 100:
        return total
    return max(1, min(total, math.ceil(total * percentage / 100)))


def _stable_shuffle(ids: Sequence[str], seed: int, salt: str) -> list[str]:
    return sorted(
        (str(item) for item in ids),
        key=lambda item: (hashlib.sha256(f"{seed}|{salt}|{item}".encode("utf-8")).hexdigest(), item),
    )


def _validate_split_fractions(train_fraction: float, validation_fraction: float, test_fraction: float) -> None:
    fractions = (train_fraction, validation_fraction, test_fraction)
    if any(value < 0 for value in fractions):
        raise ValueError("split fractions must be non-negative")
    if train_fraction <= 0:
        raise ValueError("train_fraction must be positive")
    if not math.isclose(sum(fractions), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("train/validation/test fractions must sum to 1.0")


def _dataset_entries(dataset_manifest: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    entries = list(dataset_manifest.get("recordings", ()))
    for entry in entries:
        if "recording_id" not in entry or "game" not in entry:
            raise ValueError("dataset manifest recordings must contain recording_id and game")
    return sorted(entries, key=_recording_entry_sort_key)


def _recording_game_map(dataset_manifest: Mapping[str, Any] | None) -> dict[str, str]:
    if dataset_manifest is None:
        return {}
    return {str(entry["recording_id"]): str(entry["game"]) for entry in _dataset_entries(dataset_manifest)}


def _recording_entry_sort_key(entry: Mapping[str, Any]) -> tuple[str, str]:
    return (str(entry["game"]).casefold(), str(entry["recording_id"]).casefold())


def _relative_to_or_self(path: Path, root: Path | None) -> Path:
    if root is None:
        return path
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _path_to_posix(path: Path) -> str:
    return path.as_posix()


def _scale_key(percentage: int) -> str:
    return f"{percentage}_percent"


def _round_float(value: float) -> float:
    return round(float(value), 12)


def _mean(total: int | float, count: int) -> float:
    return _round_float(total / count) if count else 0.0


def _rate(numerator: int, denominator: int) -> float:
    return _round_float(numerator / denominator) if denominator else 0.0


def _sorted_count_dict(counts: Mapping[str, int]) -> dict[str, int]:
    return {key: int(counts[key]) for key in sorted(counts, key=str.casefold)}


__all__ = [
    "ACTION_DISTRIBUTION_SCHEMA",
    "DATASET_MANIFEST_SCHEMA",
    "DEFAULT_DATASET_NAME",
    "DEFAULT_SCALE_PERCENTAGES",
    "DEFAULT_SPLIT_SEED",
    "DatasetArtifactPathError",
    "MANIFEST_STORY_ID",
    "OPTIONAL_SCALE_PERCENTAGES",
    "SCALE_MANIFEST_SCHEMA",
    "SPLIT_MANIFEST_SCHEMA",
    "action_bin_from_mapping",
    "action_bins_from_jsonable",
    "assert_artifact_path_outside_dataset_root",
    "build_action_distribution_manifest",
    "build_dataset_manifest",
    "build_held_out_game_split_manifest",
    "build_scale_manifest",
    "build_train_val_test_split_manifest",
    "load_json",
    "stable_json_dumps",
    "stable_manifest_id",
    "write_json_artifact",
]
