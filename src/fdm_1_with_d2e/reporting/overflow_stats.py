"""Dataset-wide sparse action-slot overflow statistics."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from fdm_1_with_d2e.data import D2ERecording, discover_labeled_recordings
from fdm_1_with_d2e.data.manifests import assert_artifact_path_outside_dataset_root, stable_json_dumps, write_json_artifact
from fdm_1_with_d2e.data.mcap_json import read_d2e_json_mcap_actions
from fdm_1_with_d2e.data.types import DEFAULT_BIN_WIDTH_NS, ActionBin
from fdm_1_with_d2e.reporting.temporal_sanity import bins_for_screen_span
from fdm_1_with_d2e.tokenization.action_vocab import DEFAULT_ACTION_VOCAB, DEFAULT_SPARSE_EVENT_SLOTS
from fdm_1_with_d2e.tokenization.actions import ActionTokenizer

OVERFLOW_STATS_SCHEMA = "fdm_1_with_d2e.overflow_stats.v1"
OVERFLOW_STATS_STORY_ID = "post-phase0-overflow-stats"
DEFAULT_K_SWEEP = (4, 8, 12, 16)


def sparse_candidate_tokens(action_bin: ActionBin) -> tuple[str, ...]:
    """Return sparse event tokens competing for the K event slots in one bin."""

    tokens: list[tuple[tuple[int, int, str, str, str], str]] = []
    for event in action_bin.keyboard_events:
        sort_key = (event.timestamp_ns, 0, event.key, event.event_type.value, "")
        tokens.append((sort_key, DEFAULT_ACTION_VOCAB.keyboard_token(event)))
    for event in action_bin.mouse_button_events:
        sort_key = (event.timestamp_ns, 1, event.button.value, event.event_type.value, "")
        tokens.append((sort_key, DEFAULT_ACTION_VOCAB.mouse_button_token(event)))
    for event in action_bin.scroll_events:
        for direction_index, token in enumerate(DEFAULT_ACTION_VOCAB.scroll_tokens(event)):
            sort_key = (event.timestamp_ns, 2, ",".join(direction.value for direction in event.directions), f"{event.delta_x}:{event.delta_y}", str(direction_index))
            tokens.append((sort_key, token))
    return tuple(token for _sort_key, token in sorted(tokens, key=lambda item: item[0]))


def summarize_overflow_for_bins(
    *,
    recording_id: str,
    game: str,
    bins: Sequence[ActionBin],
    slots_per_bin: int = DEFAULT_SPARSE_EVENT_SLOTS,
    k_sweep: Iterable[int] = DEFAULT_K_SWEEP,
    example_limit: int = 20,
) -> dict[str, Any]:
    """Summarize sparse-token overflow for one recording."""

    if slots_per_bin <= 0:
        raise ValueError("slots_per_bin must be positive")
    candidate_counts: list[int] = []
    histogram: Counter[int] = Counter()
    family_counts: Counter[str] = Counter()
    overflow_examples: list[dict[str, Any]] = []
    dropped_at_default: Counter[str] = Counter()
    retained_at_default: Counter[str] = Counter()
    tokenizer = ActionTokenizer(slots_per_bin=slots_per_bin)

    for action_bin in bins:
        candidates = sparse_candidate_tokens(action_bin)
        candidate_count = len(candidates)
        candidate_counts.append(candidate_count)
        histogram[candidate_count] += 1
        for token in candidates:
            family_counts[token_family_label(token)] += 1
        if candidate_count > slots_per_bin:
            tokenized = tokenizer.tokenize_bin(action_bin)
            if tokenized.overflow is not None:
                for token in tokenized.overflow.retained_tokens:
                    retained_at_default[token_family_label(token)] += 1
                for token in tokenized.overflow.dropped_tokens:
                    dropped_at_default[token_family_label(token)] += 1
            overflow_examples.append(
                {
                    "recording_id": recording_id,
                    "game": game,
                    "bin_index": action_bin.index,
                    "start_ns": action_bin.start_ns,
                    "end_ns": action_bin.end_ns,
                    "candidate_token_count": candidate_count,
                    "tokens": list(candidates),
                    "mouse_dx": action_bin.mouse_dx,
                    "mouse_dy": action_bin.mouse_dy,
                }
            )

    bin_count = len(bins)
    overflow_bin_count = sum(count > slots_per_bin for count in candidate_counts)
    k_sweep_payload = {
        str(k): {
            "overflow_bin_count": sum(count > int(k) for count in candidate_counts),
            "overflow_bin_fraction": _fraction(sum(count > int(k) for count in candidate_counts), bin_count),
        }
        for k in k_sweep
    }
    overflow_examples.sort(key=lambda item: (-int(item["candidate_token_count"]), int(item["bin_index"])))
    return {
        "schema": "fdm_1_with_d2e.recording_overflow_stats.v1",
        "recording_id": recording_id,
        "game": game,
        "bin_count": bin_count,
        "bin_width_ns": DEFAULT_BIN_WIDTH_NS,
        "slots_per_bin": slots_per_bin,
        "nonempty_sparse_bin_count": sum(count > 0 for count in candidate_counts),
        "total_sparse_candidate_tokens": sum(candidate_counts),
        "max_sparse_candidate_tokens_per_bin": max(candidate_counts, default=0),
        "overflow_bin_count": overflow_bin_count,
        "overflow_bin_fraction": _fraction(overflow_bin_count, bin_count),
        "candidate_token_count_histogram": {str(key): histogram[key] for key in sorted(histogram)},
        "candidate_token_family_counts": dict(sorted(family_counts.items())),
        "k_sweep": k_sweep_payload,
        "retained_token_family_counts_in_overflow_bins_at_default_k": dict(sorted(retained_at_default.items())),
        "dropped_token_family_counts_in_overflow_bins_at_default_k": dict(sorted(dropped_at_default.items())),
        "overflow_examples": overflow_examples[:example_limit],
    }


def summarize_dataset_overflow(
    *,
    dataset_root: str | Path,
    output_dir: str | Path,
    slots_per_bin: int = DEFAULT_SPARSE_EVENT_SLOTS,
    k_sweep: Iterable[int] = DEFAULT_K_SWEEP,
    limit_recordings: int | None = None,
    example_limit_per_recording: int = 5,
) -> dict[str, Any]:
    """Compute overflow statistics across discovered labeled D2E recordings."""

    root = Path(dataset_root)
    out = Path(output_dir)
    assert_artifact_path_outside_dataset_root(out, root)
    out.mkdir(parents=True, exist_ok=True)

    recordings = list(discover_labeled_recordings(root))
    if limit_recordings is not None:
        recordings = recordings[: int(limit_recordings)]

    recording_jsonl = out / "recording_overflow_stats.jsonl"
    failures: list[dict[str, Any]] = []
    recording_summaries: list[dict[str, Any]] = []
    with recording_jsonl.open("w", encoding="utf-8") as file_obj:
        for index, recording in enumerate(recordings, start=1):
            try:
                decoded = read_d2e_json_mcap_actions(recording.mcap_path)
                bins, span = bins_for_screen_span(decoded)
                summary = summarize_overflow_for_bins(
                    recording_id=recording.recording_id,
                    game=recording.game,
                    bins=bins,
                    slots_per_bin=slots_per_bin,
                    k_sweep=k_sweep,
                    example_limit=example_limit_per_recording,
                )
                summary["recording_index"] = index
                summary["recording_count"] = len(recordings)
                summary["relative_mcap_path"] = recording.relative_mcap_path.as_posix()
                summary["span"] = span
                recording_summaries.append(summary)
                file_obj.write(stable_json_dumps(summary))
                file_obj.write("\n")
            except Exception as exc:  # noqa: BLE001 - preserve full-dataset diagnostics.
                failure = {
                    "recording_id": recording.recording_id,
                    "game": recording.game,
                    "relative_mcap_path": recording.relative_mcap_path.as_posix(),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
                failures.append(failure)
                file_obj.write(stable_json_dumps({"schema": "fdm_1_with_d2e.recording_overflow_failure.v1", **failure}))
                file_obj.write("\n")

    aggregate = aggregate_recording_summaries(recording_summaries, slots_per_bin=slots_per_bin, k_sweep=tuple(k_sweep))
    summary = {
        "schema": OVERFLOW_STATS_SCHEMA,
        "story_id": OVERFLOW_STATS_STORY_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_root": str(root),
        "output_dir": str(out),
        "recording_count_discovered": len(discover_labeled_recordings(root)),
        "recording_count_requested": len(recordings),
        "recording_count_processed": len(recording_summaries),
        "failure_count": len(failures),
        "failures": failures[:20],
        "failures_truncated": len(failures) > 20,
        "slots_per_bin": slots_per_bin,
        "k_sweep": list(k_sweep),
        "aggregate": aggregate,
        "artifacts": {
            "recording_overflow_stats_jsonl": str(recording_jsonl),
            "summary_json": str(out / "overflow_summary.json"),
        },
    }
    write_json_artifact(summary, out / "overflow_summary.json", dataset_root=root)
    return summary


def aggregate_recording_summaries(
    summaries: Sequence[Mapping[str, Any]],
    *,
    slots_per_bin: int,
    k_sweep: Sequence[int],
) -> dict[str, Any]:
    """Aggregate recording-level summaries into dataset/game totals."""

    total_bins = sum(int(summary["bin_count"]) for summary in summaries)
    overflow_bins = sum(int(summary["overflow_bin_count"]) for summary in summaries)
    histogram: Counter[int] = Counter()
    family_counts: Counter[str] = Counter()
    dropped_counts: Counter[str] = Counter()
    retained_counts: Counter[str] = Counter()
    per_game: dict[str, dict[str, Any]] = {}
    top_examples: list[dict[str, Any]] = []

    for summary in summaries:
        game = str(summary["game"])
        game_payload = per_game.setdefault(
            game,
            {
                "recording_count": 0,
                "bin_count": 0,
                "overflow_bin_count": 0,
                "max_sparse_candidate_tokens_per_bin": 0,
            },
        )
        game_payload["recording_count"] += 1
        game_payload["bin_count"] += int(summary["bin_count"])
        game_payload["overflow_bin_count"] += int(summary["overflow_bin_count"])
        game_payload["max_sparse_candidate_tokens_per_bin"] = max(
            int(game_payload["max_sparse_candidate_tokens_per_bin"]),
            int(summary["max_sparse_candidate_tokens_per_bin"]),
        )
        for key, value in dict(summary["candidate_token_count_histogram"]).items():
            histogram[int(key)] += int(value)
        family_counts.update({key: int(value) for key, value in dict(summary["candidate_token_family_counts"]).items()})
        dropped_counts.update({key: int(value) for key, value in dict(summary["dropped_token_family_counts_in_overflow_bins_at_default_k"]).items()})
        retained_counts.update({key: int(value) for key, value in dict(summary["retained_token_family_counts_in_overflow_bins_at_default_k"]).items()})
        top_examples.extend(list(summary["overflow_examples"]))

    for game_payload in per_game.values():
        game_payload["overflow_bin_fraction"] = _fraction(game_payload["overflow_bin_count"], game_payload["bin_count"])
    top_examples.sort(key=lambda item: (-int(item["candidate_token_count"]), str(item["recording_id"]), int(item["bin_index"])))

    k_payload = {
        str(k): {
            "overflow_bin_count": sum(count for candidate_count, count in histogram.items() if candidate_count > int(k)),
            "overflow_bin_fraction": _fraction(
                sum(count for candidate_count, count in histogram.items() if candidate_count > int(k)), total_bins
            ),
        }
        for k in k_sweep
    }
    return {
        "recording_count": len(summaries),
        "bin_count": total_bins,
        "slots_per_bin": slots_per_bin,
        "nonempty_sparse_bin_count": sum(
            int(summary["nonempty_sparse_bin_count"]) for summary in summaries
        ),
        "total_sparse_candidate_tokens": sum(int(summary["total_sparse_candidate_tokens"]) for summary in summaries),
        "max_sparse_candidate_tokens_per_bin": max(
            (int(summary["max_sparse_candidate_tokens_per_bin"]) for summary in summaries), default=0
        ),
        "overflow_bin_count": overflow_bins,
        "overflow_bin_fraction": _fraction(overflow_bins, total_bins),
        "candidate_token_count_histogram": {str(key): histogram[key] for key in sorted(histogram)},
        "candidate_token_family_counts": dict(sorted(family_counts.items())),
        "retained_token_family_counts_in_overflow_bins_at_default_k": dict(sorted(retained_counts.items())),
        "dropped_token_family_counts_in_overflow_bins_at_default_k": dict(sorted(dropped_counts.items())),
        "k_sweep": k_payload,
        "per_game": dict(sorted(per_game.items())),
        "top_overflow_examples": top_examples[:100],
    }


def token_family_label(token: str) -> str:
    if token.startswith("KEY_DOWN_"):
        return "keyboard_down"
    if token.startswith("KEY_UP_"):
        return "keyboard_up"
    if token.startswith("MOUSE_"):
        return "mouse_button"
    if token.startswith("SCROLL_"):
        return "scroll"
    return "other"


def availability_payload() -> dict[str, Any]:
    return {
        "schema": OVERFLOW_STATS_SCHEMA,
        "story_id": OVERFLOW_STATS_STORY_ID,
        "status": "overflow_stats_available",
        "offline_only": True,
        "requires_dataset_root_for_real_stats": True,
        "default_slots_per_bin": DEFAULT_SPARSE_EVENT_SLOTS,
        "default_k_sweep": list(DEFAULT_K_SWEEP),
    }


def _fraction(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return float(numerator) / float(denominator)


__all__ = [
    "DEFAULT_K_SWEEP",
    "OVERFLOW_STATS_SCHEMA",
    "OVERFLOW_STATS_STORY_ID",
    "aggregate_recording_summaries",
    "availability_payload",
    "sparse_candidate_tokens",
    "summarize_dataset_overflow",
    "summarize_overflow_for_bins",
    "token_family_label",
]
