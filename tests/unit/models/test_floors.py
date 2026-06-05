from __future__ import annotations

import pytest

from fdm_1_with_d2e.data.types import (
    ActionBin,
    KeyboardEvent,
    KeyboardEventType,
    MouseButton,
    MouseButtonEvent,
    MouseButtonEventType,
    ScrollEvent,
)
from fdm_1_with_d2e.models.floors import (
    NO_SUCCESS_CLAIM,
    PLACEHOLDER_STATUS,
    all_floor_contracts,
    all_floor_scaffolds,
    fdm_action_only_floor,
    fdm_no_op_floor,
    fdm_previous_action_floor,
    fdm_video_only_floor,
    idm_action_frequency_floor,
    idm_ce_floor,
    idm_mlm_floor,
    idm_no_op_floor,
)


def _template(index: int, start_ns: int = 0) -> ActionBin:
    return ActionBin(index=index, start_ns=start_ns, end_ns=start_ns + 50_000_000, mouse_dx=99, mouse_dy=-5)


def test_all_floor_contracts_are_explicit_diagnostic_placeholders() -> None:
    contracts = all_floor_contracts()
    assert {contract.floor_id for contract in contracts} == {
        "idm-no-op-zero-mouse-floor-v0",
        "idm-action-frequency-floor-v0",
        "idm-ce-one-shot-classifier-diagnostic-v0",
        "idm-mlm-random-mask-denoising-diagnostic-v0",
        "fdm-b0-no-op-zero-mouse-floor-v0",
        "fdm-b1-previous-action-repeat-floor-v0",
        "fdm-b2-action-only-diagnostic-v0",
        "fdm-b3-video-only-diagnostic-v0",
    }

    for scaffold in all_floor_scaffolds():
        payload = scaffold.describe()
        assert payload["status"] == PLACEHOLDER_STATUS
        assert payload["diagnostic_only"] is True
        assert payload["is_trained_model"] is False
        assert payload["permits_success_claim"] is False
        assert payload["checkpoint_id"] is None
        assert NO_SUCCESS_CLAIM in payload["notes"]
        assert scaffold.is_trained_model is False
        assert scaffold.permits_success_claim is False
        with pytest.raises(NotImplementedError, match="fitting|training"):
            scaffold.fit([])
        with pytest.raises(NotImplementedError, match="no checkpoint|checkpoint"):
            scaffold.load_checkpoint("checkpoint.pt")


def test_no_op_floors_return_deterministic_zero_mouse_no_sparse_events() -> None:
    templates = (_template(0), _template(1, 50_000_000))

    for floor in (idm_no_op_floor(), fdm_no_op_floor()):
        result = floor.predict_bins(templates)
        assert result.status == PLACEHOLDER_STATUS
        assert result.deterministic is True
        assert result.quality_claim is False
        assert "zero-mouse" in " ".join(result.notes)
        assert [(bin.index, bin.start_ns, bin.end_ns) for bin in result.predicted_bins] == [
            (0, 0, 50_000_000),
            (1, 50_000_000, 100_000_000),
        ]
        assert all(bin.mouse_dx == 0 and bin.mouse_dy == 0 for bin in result.predicted_bins)
        assert all(bin.sparse_event_count == 0 for bin in result.predicted_bins)


def test_previous_action_floor_repeats_content_and_remaps_timestamps() -> None:
    previous = ActionBin(
        index=4,
        start_ns=200_000_000,
        end_ns=250_000_000,
        mouse_dx=12,
        mouse_dy=-7,
        keyboard_events=(KeyboardEvent(210_000_000, "KEY_A", KeyboardEventType.DOWN),),
        mouse_button_events=(MouseButtonEvent(225_000_000, MouseButton.LEFT, MouseButtonEventType.UP),),
        scroll_events=(ScrollEvent(249_000_000, delta_y=-1),),
    )
    target = ActionBin(index=5, start_ns=250_000_000, end_ns=300_000_000)

    result = fdm_previous_action_floor().predict_bins((target,), context={"previous_action": previous})
    repeated = result.predicted_bins[0]

    assert result.quality_claim is False
    assert repeated.index == target.index
    assert repeated.start_ns == target.start_ns
    assert repeated.end_ns == target.end_ns
    assert (repeated.mouse_dx, repeated.mouse_dy) == (12, -7)
    assert repeated.keyboard_events == (KeyboardEvent(260_000_000, "KEY_A", KeyboardEventType.DOWN),)
    assert repeated.mouse_button_events == (
        MouseButtonEvent(275_000_000, MouseButton.LEFT, MouseButtonEventType.UP),
    )
    assert repeated.scroll_events == (ScrollEvent(299_000_000, delta_y=-1),)


def test_previous_action_floor_without_context_falls_back_to_no_op() -> None:
    result = fdm_previous_action_floor().predict_bins((_template(0),), context={})
    assert result.predicted_bins[0].mouse_dx == 0
    assert result.predicted_bins[0].mouse_dy == 0
    assert result.predicted_bins[0].sparse_event_count == 0
    assert any("falls back to no-op" in note for note in result.notes)


def test_nontrivial_floor_predictions_raise_explicit_not_implemented_boundaries() -> None:
    template = (_template(0),)

    with pytest.raises(NotImplementedError, match="action-distribution artifact"):
        idm_action_frequency_floor().predict_bins(template)
    with pytest.raises(NotImplementedError, match="IDM objective diagnostic"):
        idm_ce_floor().predict_bins(template, context={"video_features": []})
    with pytest.raises(NotImplementedError, match="IDM objective diagnostic"):
        idm_mlm_floor().predict_bins(template, context={"masked_actions": []})
    with pytest.raises(NotImplementedError, match="action-only model"):
        fdm_action_only_floor().predict_bins(template, context={"action_history": []})
    with pytest.raises(NotImplementedError, match="video features"):
        fdm_video_only_floor().predict_bins(template, context={"video_features": []})
