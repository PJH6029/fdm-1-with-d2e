"""Offline D2E-style primary action metrics over canonical 50ms bins.

The official D2E ``evaluate.py`` remains the headline path for real MCAP runs.
This module provides the local, dependency-light fixture evaluator required for
Phase 0: it consumes canonical ``ActionBin`` objects, uses the same 50ms action
unit, and reports every local formula/reimplementation boundary in JSON-friendly
records.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import math
from typing import Any

from fdm_1_with_d2e.data.types import (
    DEFAULT_BIN_WIDTH_MS,
    DEFAULT_BIN_WIDTH_NS,
    ActionBin,
    KeyboardEvent,
    MouseButtonEvent,
)

EVALUATOR_STORY_ID = "G005-implement-evaluator-and-official-d2e"
LOCAL_EVALUATOR_ID = "phase0-d2e-local-fixture-v1"
LOCAL_METRIC_REVISION = "d2e-local-50ms-actionbin-v1"
EVALUATION_METRICS_SCHEMA = "schemas/evaluation_metrics.schema.json"

MOUSE_PEARSON_X = "mouse_pearson_x"
MOUSE_PEARSON_Y = "mouse_pearson_y"
MOUSE_SCALE_RATIO_X = "mouse_scale_ratio_x"
MOUSE_SCALE_RATIO_Y = "mouse_scale_ratio_y"
MOUSE_BUTTON_ACCURACY = "mouse_button_accuracy"
KEYBOARD_KEY_ACCURACY = "keyboard_key_accuracy"
PRIMARY_METRIC_NAMES: tuple[str, ...] = (
    MOUSE_PEARSON_X,
    MOUSE_PEARSON_Y,
    MOUSE_SCALE_RATIO_X,
    MOUSE_SCALE_RATIO_Y,
    MOUSE_BUTTON_ACCURACY,
    KEYBOARD_KEY_ACCURACY,
)

_EPSILON = 1e-12
_EXTREME_SCALE_RATIO = 10.0

JSONDict = dict[str, Any]


@dataclass(frozen=True, slots=True)
class D2EEvaluationRecording:
    """One recording's ground-truth/predicted canonical-bin pair for metrics."""

    recording_id: str
    game: str
    ground_truth_bins: tuple[ActionBin, ...]
    predicted_bins: tuple[ActionBin, ...]


@dataclass(frozen=True, slots=True)
class _BinPair:
    ground_truth: ActionBin
    predicted: ActionBin


def compute_d2e_primary_metrics(
    ground_truth_bins: Iterable[ActionBin],
    predicted_bins: Iterable[ActionBin],
    *,
    group: Mapping[str, Any] | None = None,
    strict_timestamps: bool = True,
    evaluator_id: str = LOCAL_EVALUATOR_ID,
    metric_revision: str = LOCAL_METRIC_REVISION,
) -> JSONDict:
    """Compute local D2E-style primary metrics for one bin group.

    Mouse metrics use aggregate raw ``mouse_dx``/``mouse_dy`` values already
    aligned to non-overlapping 50ms bins. Sparse-event accuracies compare exact
    per-bin count multisets for D2E keyboard key/type and mouse-button/type
    transitions. ``None`` metric values represent explicit ``NA`` cases.
    """

    pairs = _validate_bin_pairs(
        tuple(ground_truth_bins),
        tuple(predicted_bins),
        strict_timestamps=strict_timestamps,
    )
    gt_bins = tuple(pair.ground_truth for pair in pairs)
    pred_bins = tuple(pair.predicted for pair in pairs)

    metrics = {
        MOUSE_PEARSON_X: _pearson_metric(MOUSE_PEARSON_X, _axis_values(gt_bins, "x"), _axis_values(pred_bins, "x")),
        MOUSE_PEARSON_Y: _pearson_metric(MOUSE_PEARSON_Y, _axis_values(gt_bins, "y"), _axis_values(pred_bins, "y")),
        MOUSE_SCALE_RATIO_X: _scale_ratio_metric(
            MOUSE_SCALE_RATIO_X,
            _axis_values(gt_bins, "x"),
            _axis_values(pred_bins, "x"),
        ),
        MOUSE_SCALE_RATIO_Y: _scale_ratio_metric(
            MOUSE_SCALE_RATIO_Y,
            _axis_values(gt_bins, "y"),
            _axis_values(pred_bins, "y"),
        ),
        MOUSE_BUTTON_ACCURACY: _count_match_accuracy_metric(
            MOUSE_BUTTON_ACCURACY,
            gt_bins,
            pred_bins,
            family="mouse_button",
        ),
        KEYBOARD_KEY_ACCURACY: _count_match_accuracy_metric(
            KEYBOARD_KEY_ACCURACY,
            gt_bins,
            pred_bins,
            family="keyboard",
        ),
    }

    return {
        "schema": EVALUATION_METRICS_SCHEMA,
        "evaluator_id": evaluator_id,
        "metric_revision": metric_revision,
        "created_by_story": EVALUATOR_STORY_ID,
        "timebase_ms": DEFAULT_BIN_WIDTH_MS,
        "aggregation": "micro",
        "group": dict(group or {}),
        "coverage": _coverage(gt_bins),
        "metrics": metrics,
        "formula_notes": {
            "mouse_pearson": "population Pearson correlation over per-bin raw axis deltas; NA when either axis series has zero variance or <2 bins",
            "mouse_scale_ratio": "unsigned population-standard-deviation scale ratio max(std_gt,std_pred)/min(std_gt,std_pred), always >=1 when defined; NA for zero/near-zero scale",
            "mouse_button_accuracy": "per-bin exact count-multiset match for left/right/middle down/up events",
            "keyboard_key_accuracy": "per-bin exact count-multiset match by key and keyboard event type",
            "official_boundary": "fixture reimplementation; real MCAP headline runs should invoke pinned D2E evaluate.py or record deviations",
        },
    }


def evaluate_d2e_recordings(
    recordings: Iterable[D2EEvaluationRecording],
    *,
    strict_timestamps: bool = True,
    evaluator_id: str = LOCAL_EVALUATOR_ID,
    metric_revision: str = LOCAL_METRIC_REVISION,
) -> JSONDict:
    """Compute micro, per-recording, per-game, and per-game macro metrics."""

    items = tuple(recordings)
    per_recording: dict[str, JSONDict] = {}
    per_game_bins: dict[str, list[tuple[ActionBin, ActionBin]]] = defaultdict(list)
    all_pairs: list[tuple[ActionBin, ActionBin]] = []

    for item in items:
        payload = compute_d2e_primary_metrics(
            item.ground_truth_bins,
            item.predicted_bins,
            group={"recording_id": item.recording_id, "game": item.game},
            strict_timestamps=strict_timestamps,
            evaluator_id=evaluator_id,
            metric_revision=metric_revision,
        )
        per_recording[item.recording_id] = payload
        pairs = tuple(zip(item.ground_truth_bins, item.predicted_bins, strict=True))
        per_game_bins[item.game].extend(pairs)
        all_pairs.extend(pairs)

    micro = compute_d2e_primary_metrics(
        (gt for gt, _pred in all_pairs),
        (pred for _gt, pred in all_pairs),
        group={"recording_count": len(items), "scope": "all_recordings"},
        strict_timestamps=strict_timestamps,
        evaluator_id=evaluator_id,
        metric_revision=metric_revision,
    )

    per_game: dict[str, JSONDict] = {}
    for game, pairs in sorted(per_game_bins.items()):
        per_game[game] = compute_d2e_primary_metrics(
            (gt for gt, _pred in pairs),
            (pred for _gt, pred in pairs),
            group={"game": game, "recording_count": sum(1 for item in items if item.game == game)},
            strict_timestamps=strict_timestamps,
            evaluator_id=evaluator_id,
            metric_revision=metric_revision,
        )

    return {
        "schema": EVALUATION_METRICS_SCHEMA,
        "evaluator_id": evaluator_id,
        "metric_revision": metric_revision,
        "created_by_story": EVALUATOR_STORY_ID,
        "timebase_ms": DEFAULT_BIN_WIDTH_MS,
        "aggregation": "recording_collection",
        "coverage": {
            "recording_count": len(items),
            "game_count": len(per_game),
            "games": sorted(per_game),
            "bin_count": micro["coverage"]["bin_count"],
            "active_action_bin_count": micro["coverage"]["active_action_bin_count"],
        },
        "micro": micro,
        "per_recording": per_recording,
        "per_game": per_game,
        "per_game_macro": macro_average_metric_groups(per_game.values(), group_label="game"),
    }


def macro_average_metric_groups(metric_groups: Iterable[Mapping[str, Any]], *, group_label: str) -> JSONDict:
    """Average metric values equally across already-computed groups.

    ``NA`` values remain explicit and are excluded from the macro mean while the
    eligible/NA group counts are reported for every metric.
    """

    groups = tuple(metric_groups)
    macro_metrics: dict[str, JSONDict] = {}
    for metric_name in PRIMARY_METRIC_NAMES:
        values: list[float] = []
        na_count = 0
        for group in groups:
            metric = group.get("metrics", {}).get(metric_name)
            if not isinstance(metric, Mapping):
                na_count += 1
                continue
            value = metric.get("value")
            if value is None:
                na_count += 1
            else:
                values.append(float(value))
        if values:
            value: float | None = sum(values) / len(values)
            status = "ok"
            na_reason = None
        else:
            value = None
            status = "NA"
            na_reason = f"no eligible {group_label} metric values"
        macro_metrics[metric_name] = {
            "value": _round_float(value),
            "status": status,
            "eligible_group_count": len(values),
            "na_group_count": na_count,
            "total_group_count": len(groups),
            "na_reason": na_reason,
            "formula": f"unweighted mean of per-{group_label} {metric_name} values, excluding NA",
        }

    return {
        "aggregation": f"per_{group_label}_macro",
        "group_count": len(groups),
        "metrics": macro_metrics,
    }


def metric_values(metrics_payload: Mapping[str, Any]) -> dict[str, float | None]:
    """Return a compact ``metric_name -> value|None`` view for assertions/reports."""

    metrics = metrics_payload.get("metrics", {})
    return {
        name: (None if metrics[name].get("value") is None else float(metrics[name]["value"]))
        for name in PRIMARY_METRIC_NAMES
        if name in metrics
    }


def _validate_bin_pairs(
    ground_truth_bins: tuple[ActionBin, ...],
    predicted_bins: tuple[ActionBin, ...],
    *,
    strict_timestamps: bool,
) -> tuple[_BinPair, ...]:
    if len(ground_truth_bins) != len(predicted_bins):
        raise ValueError(
            f"ground_truth_bins and predicted_bins must have the same length, got "
            f"{len(ground_truth_bins)} and {len(predicted_bins)}"
        )
    pairs: list[_BinPair] = []
    for index, (ground_truth, predicted) in enumerate(zip(ground_truth_bins, predicted_bins, strict=True)):
        if strict_timestamps and (
            ground_truth.index != predicted.index
            or ground_truth.start_ns != predicted.start_ns
            or ground_truth.end_ns != predicted.end_ns
        ):
            raise ValueError(
                "ground-truth and predicted bins must align by index/start/end; "
                f"mismatch at pair {index}: "
                f"gt=({ground_truth.index},{ground_truth.start_ns},{ground_truth.end_ns}) "
                f"pred=({predicted.index},{predicted.start_ns},{predicted.end_ns})"
            )
        if ground_truth.end_ns <= ground_truth.start_ns or predicted.end_ns <= predicted.start_ns:
            raise ValueError(f"bin {index} has non-positive duration")
        pairs.append(_BinPair(ground_truth=ground_truth, predicted=predicted))
    return tuple(pairs)


def _axis_values(action_bins: Sequence[ActionBin], axis: str) -> tuple[float, ...]:
    if axis == "x":
        return tuple(float(action_bin.mouse_dx) for action_bin in action_bins)
    if axis == "y":
        return tuple(float(action_bin.mouse_dy) for action_bin in action_bins)
    raise ValueError(f"unsupported mouse axis: {axis!r}")


def _pearson_metric(name: str, ground_truth: Sequence[float], predicted: Sequence[float]) -> JSONDict:
    sample_count = len(ground_truth)
    if sample_count < 2:
        return _na_metric(name, sample_count, "insufficient_bins", "population Pearson correlation")
    gt_mean, gt_ss = _mean_and_sum_squares(ground_truth)
    pred_mean, pred_ss = _mean_and_sum_squares(predicted)
    if gt_ss <= _EPSILON or pred_ss <= _EPSILON:
        return _na_metric(name, sample_count, "zero_variance_axis", "population Pearson correlation")
    covariance = sum((gt - gt_mean) * (pred - pred_mean) for gt, pred in zip(ground_truth, predicted, strict=True))
    value = covariance / math.sqrt(gt_ss * pred_ss)
    value = max(-1.0, min(1.0, value))
    return {
        "value": _round_float(value),
        "status": "ok",
        "sample_count": sample_count,
        "na_reason": None,
        "formula": "sum((gt-mean_gt)*(pred-mean_pred)) / sqrt(sum((gt-mean_gt)^2)*sum((pred-mean_pred)^2))",
        "gt_mean": _round_float(gt_mean),
        "pred_mean": _round_float(pred_mean),
    }


def _scale_ratio_metric(name: str, ground_truth: Sequence[float], predicted: Sequence[float]) -> JSONDict:
    sample_count = len(ground_truth)
    if sample_count < 2:
        return _na_metric(name, sample_count, "insufficient_bins", "unsigned stddev scale ratio")
    _gt_mean, gt_ss = _mean_and_sum_squares(ground_truth)
    _pred_mean, pred_ss = _mean_and_sum_squares(predicted)
    gt_scale = math.sqrt(gt_ss / sample_count)
    pred_scale = math.sqrt(pred_ss / sample_count)
    flags: list[str] = []
    if gt_scale <= _EPSILON:
        flags.append("near_zero_gt_axis_scale")
    if pred_scale <= _EPSILON:
        flags.append("near_zero_pred_axis_scale")
    if flags:
        payload = _na_metric(name, sample_count, "zero_or_near_zero_axis_scale", "unsigned stddev scale ratio")
        payload["gt_scale"] = _round_float(gt_scale)
        payload["pred_scale"] = _round_float(pred_scale)
        payload["flags"] = flags
        return payload
    value = max(gt_scale, pred_scale) / min(gt_scale, pred_scale)
    if value >= _EXTREME_SCALE_RATIO:
        flags.append("extreme_scale_ratio")
    return {
        "value": _round_float(value),
        "status": "ok",
        "sample_count": sample_count,
        "na_reason": None,
        "formula": "max(population_stddev_gt,population_stddev_pred) / min(population_stddev_gt,population_stddev_pred)",
        "gt_scale": _round_float(gt_scale),
        "pred_scale": _round_float(pred_scale),
        "flags": flags,
    }


def _count_match_accuracy_metric(
    name: str,
    ground_truth_bins: Sequence[ActionBin],
    predicted_bins: Sequence[ActionBin],
    *,
    family: str,
) -> JSONDict:
    total_bins = len(ground_truth_bins)
    if total_bins == 0:
        return _na_metric(name, 0, "no_bins", f"per-bin {family} count-multiset match accuracy")
    matched_bins = 0
    mismatch_examples: list[JSONDict] = []
    for ground_truth, predicted in zip(ground_truth_bins, predicted_bins, strict=True):
        if family == "mouse_button":
            gt_counts = _mouse_button_count_multiset(ground_truth.mouse_button_events)
            pred_counts = _mouse_button_count_multiset(predicted.mouse_button_events)
        elif family == "keyboard":
            gt_counts = _keyboard_count_multiset(ground_truth.keyboard_events)
            pred_counts = _keyboard_count_multiset(predicted.keyboard_events)
        else:  # pragma: no cover - defensive branch for future families.
            raise ValueError(f"unsupported count-match family: {family!r}")
        if gt_counts == pred_counts:
            matched_bins += 1
        elif len(mismatch_examples) < 5:
            mismatch_examples.append(
                {
                    "bin_index": ground_truth.index,
                    "ground_truth_counts": _counter_to_json(gt_counts),
                    "predicted_counts": _counter_to_json(pred_counts),
                }
            )
    return {
        "value": _round_float(matched_bins / total_bins),
        "status": "ok",
        "total_bins": total_bins,
        "matched_bins": matched_bins,
        "mismatched_bins": total_bins - matched_bins,
        "na_reason": None,
        "formula": f"matched_bins / total_bins where each bin compares exact {family} count multiset",
        "mismatch_examples": mismatch_examples,
    }


def _mouse_button_count_multiset(events: Iterable[MouseButtonEvent]) -> Counter[tuple[str, str]]:
    return Counter((event.button.value, event.event_type.value) for event in events)


def _keyboard_count_multiset(events: Iterable[KeyboardEvent]) -> Counter[tuple[str, str]]:
    return Counter((event.key, event.event_type.value) for event in events)


def _counter_to_json(counter: Counter[tuple[str, str]]) -> dict[str, int]:
    return {f"{key}:{event_type}": count for (key, event_type), count in sorted(counter.items())}


def _coverage(action_bins: Sequence[ActionBin]) -> JSONDict:
    active = sum(1 for action_bin in action_bins if action_bin.has_mouse_motion or action_bin.sparse_event_count > 0)
    return {
        "bin_count": len(action_bins),
        "active_action_bin_count": active,
        "no_op_bin_count": len(action_bins) - active,
        "timebase_ms": DEFAULT_BIN_WIDTH_MS,
        "bin_width_ns": DEFAULT_BIN_WIDTH_NS,
    }


def _mean_and_sum_squares(values: Sequence[float]) -> tuple[float, float]:
    mean = sum(values) / len(values)
    sum_squares = sum((value - mean) ** 2 for value in values)
    return mean, sum_squares


def _na_metric(name: str, sample_count: int, reason: str, formula: str) -> JSONDict:
    return {
        "value": None,
        "status": "NA",
        "sample_count": sample_count,
        "na_reason": reason,
        "formula": formula,
    }


def _round_float(value: float | None) -> float | None:
    if value is None:
        return None
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"metric value must be finite or None, got {value!r}")
    # Avoid emitting -0.0 in JSON evidence.
    rounded = round(float(value), 12)
    return 0.0 if rounded == 0 else rounded


__all__ = [
    "D2EEvaluationRecording",
    "EVALUATION_METRICS_SCHEMA",
    "EVALUATOR_STORY_ID",
    "KEYBOARD_KEY_ACCURACY",
    "LOCAL_EVALUATOR_ID",
    "LOCAL_METRIC_REVISION",
    "MOUSE_BUTTON_ACCURACY",
    "MOUSE_PEARSON_X",
    "MOUSE_PEARSON_Y",
    "MOUSE_SCALE_RATIO_X",
    "MOUSE_SCALE_RATIO_Y",
    "PRIMARY_METRIC_NAMES",
    "compute_d2e_primary_metrics",
    "evaluate_d2e_recordings",
    "macro_average_metric_groups",
    "metric_values",
]
