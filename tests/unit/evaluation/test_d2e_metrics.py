from __future__ import annotations

import math

import pytest

from fdm_1_with_d2e.data import (
    ActionBin,
    KeyboardEvent,
    KeyboardEventType,
    MouseButton,
    MouseButtonEvent,
    MouseButtonEventType,
)
from fdm_1_with_d2e.evaluation import (
    D2EEvaluationRecording,
    KEYBOARD_KEY_ACCURACY,
    MOUSE_BUTTON_ACCURACY,
    MOUSE_PEARSON_X,
    MOUSE_PEARSON_Y,
    MOUSE_SCALE_RATIO_X,
    MOUSE_SCALE_RATIO_Y,
    compute_d2e_primary_metrics,
    evaluate_d2e_recordings,
    metric_values,
)

WIDTH = 50_000_000


def _bin(
    index: int,
    dx: int,
    dy: int,
    *,
    keys: tuple[tuple[str, KeyboardEventType], ...] = (),
    buttons: tuple[tuple[MouseButton, MouseButtonEventType], ...] = (),
) -> ActionBin:
    start = index * WIDTH
    return ActionBin(
        index=index,
        start_ns=start,
        end_ns=start + WIDTH,
        mouse_dx=dx,
        mouse_dy=dy,
        keyboard_events=tuple(
            KeyboardEvent(timestamp_ns=start + 1_000_000 + event_index, key=key, event_type=event_type)
            for event_index, (key, event_type) in enumerate(keys)
        ),
        mouse_button_events=tuple(
            MouseButtonEvent(timestamp_ns=start + 2_000_000 + event_index, button=button, event_type=event_type)
            for event_index, (button, event_type) in enumerate(buttons)
        ),
    )


def test_perfect_bins_have_unit_metrics() -> None:
    bins = (
        _bin(0, -2, 4, keys=(("KEY_A", KeyboardEventType.DOWN),)),
        _bin(1, 0, 0, buttons=((MouseButton.LEFT, MouseButtonEventType.DOWN),)),
        _bin(
            2,
            2,
            -4,
            keys=(("KEY_A", KeyboardEventType.UP),),
            buttons=((MouseButton.LEFT, MouseButtonEventType.UP),),
        ),
    )

    payload = compute_d2e_primary_metrics(bins, bins)
    values = metric_values(payload)

    assert values == {
        MOUSE_PEARSON_X: 1.0,
        MOUSE_PEARSON_Y: 1.0,
        MOUSE_SCALE_RATIO_X: 1.0,
        MOUSE_SCALE_RATIO_Y: 1.0,
        MOUSE_BUTTON_ACCURACY: 1.0,
        KEYBOARD_KEY_ACCURACY: 1.0,
    }
    assert payload["coverage"]["active_action_bin_count"] == 3


def test_scale_ratio_is_unsigned_and_pearson_preserves_sign() -> None:
    gt = (_bin(0, -1, -2), _bin(1, 0, 0), _bin(2, 1, 2))
    pred = (_bin(0, 2, -4), _bin(1, 0, 0), _bin(2, -2, 4))

    values = metric_values(compute_d2e_primary_metrics(gt, pred))

    assert values[MOUSE_PEARSON_X] == -1.0
    assert values[MOUSE_PEARSON_Y] == 1.0
    assert values[MOUSE_SCALE_RATIO_X] == 2.0
    assert values[MOUSE_SCALE_RATIO_Y] == 2.0
    assert values[MOUSE_SCALE_RATIO_X] >= 1.0
    assert values[MOUSE_SCALE_RATIO_Y] >= 1.0


def test_zero_variance_mouse_axes_are_explicit_na() -> None:
    gt = (_bin(0, 0, 0), _bin(1, 0, 0))
    pred = (_bin(0, 0, 1), _bin(1, 0, 1))

    payload = compute_d2e_primary_metrics(gt, pred)

    assert payload["metrics"][MOUSE_PEARSON_X]["status"] == "NA"
    assert payload["metrics"][MOUSE_PEARSON_X]["value"] is None
    assert payload["metrics"][MOUSE_SCALE_RATIO_X]["status"] == "NA"
    assert payload["metrics"][MOUSE_SCALE_RATIO_X]["flags"] == [
        "near_zero_gt_axis_scale",
        "near_zero_pred_axis_scale",
    ]


def test_sparse_event_count_match_accuracy_uses_exact_per_bin_multisets() -> None:
    gt = (
        _bin(0, -1, 0, keys=(("KEY_A", KeyboardEventType.DOWN),)),
        _bin(1, 0, 1, buttons=((MouseButton.LEFT, MouseButtonEventType.DOWN),)),
        _bin(2, 1, 0, buttons=((MouseButton.RIGHT, MouseButtonEventType.UP),)),
    )
    pred = (
        _bin(0, -1, 0, keys=(("KEY_B", KeyboardEventType.DOWN),)),  # keyboard mismatch
        _bin(1, 0, 1, buttons=((MouseButton.LEFT, MouseButtonEventType.DOWN),)),
        _bin(2, 1, 0, buttons=((MouseButton.RIGHT, MouseButtonEventType.DOWN),)),  # button type mismatch
    )

    payload = compute_d2e_primary_metrics(gt, pred)

    assert payload["metrics"][KEYBOARD_KEY_ACCURACY]["matched_bins"] == 2
    assert payload["metrics"][KEYBOARD_KEY_ACCURACY]["value"] == pytest.approx(2 / 3)
    assert payload["metrics"][MOUSE_BUTTON_ACCURACY]["matched_bins"] == 2
    assert payload["metrics"][MOUSE_BUTTON_ACCURACY]["value"] == pytest.approx(2 / 3)
    assert payload["metrics"][KEYBOARD_KEY_ACCURACY]["mismatch_examples"][0]["bin_index"] == 0
    assert payload["metrics"][MOUSE_BUTTON_ACCURACY]["mismatch_examples"][0]["bin_index"] == 2


def test_collection_metrics_include_per_game_macro_excluding_na() -> None:
    game_a = D2EEvaluationRecording(
        recording_id="a/0",
        game="game-a",
        ground_truth_bins=(_bin(0, -1, -1), _bin(1, 1, 1)),
        predicted_bins=(_bin(0, -1, -1), _bin(1, 1, 1)),
    )
    game_b = D2EEvaluationRecording(
        recording_id="b/0",
        game="game-b",
        ground_truth_bins=(_bin(0, 0, 0), _bin(1, 0, 0)),
        predicted_bins=(_bin(0, 0, 0), _bin(1, 0, 0)),
    )

    payload = evaluate_d2e_recordings((game_a, game_b))

    assert payload["coverage"]["recording_count"] == 2
    assert payload["coverage"]["game_count"] == 2
    assert set(payload["per_game"]) == {"game-a", "game-b"}
    macro_x = payload["per_game_macro"]["metrics"][MOUSE_PEARSON_X]
    assert macro_x["value"] == 1.0
    assert macro_x["eligible_group_count"] == 1
    assert macro_x["na_group_count"] == 1


def test_mismatched_bin_lengths_and_timestamps_raise() -> None:
    with pytest.raises(ValueError, match="same length"):
        compute_d2e_primary_metrics((_bin(0, 0, 0),), ())

    with pytest.raises(ValueError, match="align"):
        compute_d2e_primary_metrics((_bin(0, 0, 0),), (_bin(1, 0, 0),))
