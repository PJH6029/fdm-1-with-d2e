from __future__ import annotations

import pytest

from fdm_1_with_d2e.video.scaffold import (
    PROBE_NO_PROMOTION_CLAIM,
    PROBE_PLACEHOLDER_STATUS,
    ProbeTaskFamily,
    default_frozen_encoder_probe_contract,
    frozen_encoder_probe_scaffold,
    summarize_probe_contract,
)


def test_frozen_encoder_probe_contract_is_non_promoting_placeholder() -> None:
    contract = default_frozen_encoder_probe_contract(encoder_candidate_id="vjepa2-placeholder")
    payload = contract.as_dict()

    assert payload["status"] == PROBE_PLACEHOLDER_STATUS
    assert payload["encoder_candidate_id"] == "vjepa2-placeholder"
    assert payload["requires_frozen_encoder"] is True
    assert payload["is_trained_probe"] is False
    assert payload["is_encoder_loaded"] is False
    assert payload["permits_ve_promotion"] is False
    assert PROBE_NO_PROMOTION_CLAIM in payload["notes"]
    assert set(payload["task_families"]) >= {
        ProbeTaskFamily.MOUSE.value,
        ProbeTaskFamily.KEYBOARD.value,
        ProbeTaskFamily.MOUSE_BUTTON.value,
        ProbeTaskFamily.SCROLL.value,
        ProbeTaskFamily.CURSOR_CROSSHAIR.value,
        ProbeTaskFamily.HUD_UI_TEXT.value,
        ProbeTaskFamily.TINY_IDM_TRANSFER.value,
        ProbeTaskFamily.TINY_FDM_TRANSFER.value,
    }
    assert {"micro", "per_game_macro", "held_out_game_macro"}.issubset(payload["required_aggregations"])


def test_frozen_encoder_probe_scaffold_rejects_unimplemented_model_operations() -> None:
    scaffold = frozen_encoder_probe_scaffold(encoder_candidate_id="videomae-placeholder")
    description = scaffold.describe()
    summary = summarize_probe_contract(description)

    assert scaffold.status == PROBE_PLACEHOLDER_STATUS
    assert scaffold.is_trained_probe is False
    assert scaffold.permits_ve_promotion is False
    assert summary["status"] == PROBE_PLACEHOLDER_STATUS
    assert summary["is_trained_probe"] is False
    assert summary["permits_ve_promotion"] is False
    assert summary["task_family_count"] >= 8

    with pytest.raises(NotImplementedError, match="feature extraction"):
        scaffold.extract_features([])
    with pytest.raises(NotImplementedError, match="probe fitting"):
        scaffold.fit_probe([])
    with pytest.raises(NotImplementedError, match="no VE probe metrics"):
        scaffold.evaluate_probe([])
