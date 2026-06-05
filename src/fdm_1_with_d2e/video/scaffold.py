"""Frozen video-encoder probe scaffold contracts for later VE domain-gap checks.

The Phase 0 scaffold records what a frozen-encoder probe pass must prove, but it
never loads an encoder, extracts features, trains probes, or promotes a video
encoder.  Later VE stories must replace this with verified feature-cache/probe
implementations and run records.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

VE_PROBE_SCAFFOLD_STORY_ID = "G006-implement-floor-and-probe-scaffolds"
PROBE_PLACEHOLDER_STATUS = "frozen_encoder_probe_placeholder_only_not_trained"
PROBE_NO_PROMOTION_CLAIM = "probe scaffold only; cannot promote a VE candidate or claim domain adaptation success"


class ProbeTaskFamily(str, Enum):
    """Probe task groups required by the video-encoder evaluation spec."""

    MOUSE = "mouse"
    KEYBOARD = "keyboard"
    MOUSE_BUTTON = "mouse_button"
    SCROLL = "scroll"
    CURSOR_CROSSHAIR = "cursor_crosshair"
    HUD_UI_TEXT = "hud_ui_text"
    NEXT_CLICK = "next_click"
    TINY_IDM_TRANSFER = "tiny_idm_transfer"
    TINY_FDM_TRANSFER = "tiny_fdm_transfer"


@dataclass(frozen=True, slots=True)
class FrozenEncoderProbeContract:
    """Serializable contract for VE frozen-encoder probe evidence."""

    probe_id: str
    encoder_candidate_id: str
    feature_source: str
    task_families: tuple[ProbeTaskFamily, ...]
    metric_families: tuple[str, ...]
    required_aggregations: tuple[str, ...]
    evidence_required: tuple[str, ...]
    later_phase: str = "Phase 1 video-encoder bakeoff/domain-gap checks"
    status: str = PROBE_PLACEHOLDER_STATUS
    created_by_story: str = VE_PROBE_SCAFFOLD_STORY_ID
    requires_frozen_encoder: bool = True
    is_trained_probe: bool = False
    is_encoder_loaded: bool = False
    permits_ve_promotion: bool = False
    notes: tuple[str, ...] = field(default_factory=lambda: (PROBE_NO_PROMOTION_CLAIM,))

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly contract record."""

        return {
            "probe_id": self.probe_id,
            "encoder_candidate_id": self.encoder_candidate_id,
            "feature_source": self.feature_source,
            "task_families": [task.value for task in self.task_families],
            "metric_families": list(self.metric_families),
            "required_aggregations": list(self.required_aggregations),
            "evidence_required": list(self.evidence_required),
            "later_phase": self.later_phase,
            "status": self.status,
            "created_by_story": self.created_by_story,
            "requires_frozen_encoder": self.requires_frozen_encoder,
            "is_trained_probe": self.is_trained_probe,
            "is_encoder_loaded": self.is_encoder_loaded,
            "permits_ve_promotion": self.permits_ve_promotion,
            "notes": list(self.notes),
        }


class FrozenEncoderProbeScaffold:
    """Contract-only VE probe surface with explicit NotImplemented boundaries."""

    def __init__(self, contract: FrozenEncoderProbeContract | None = None) -> None:
        self.contract = contract or default_frozen_encoder_probe_contract()

    @property
    def status(self) -> str:
        return self.contract.status

    @property
    def is_trained_probe(self) -> bool:
        return False

    @property
    def permits_ve_promotion(self) -> bool:
        return False

    def describe(self) -> dict[str, Any]:
        """Return the probe contract without touching video data or models."""

        return self.contract.as_dict()

    def extract_features(self, *_args: Any, **_kwargs: Any) -> None:
        """Reject feature extraction until a later VE implementation story."""

        raise NotImplementedError(
            f"{self.contract.probe_id} is {PROBE_PLACEHOLDER_STATUS}; frozen-encoder feature extraction "
            "must be implemented and evidenced in Phase 1."
        )

    def fit_probe(self, *_args: Any, **_kwargs: Any) -> None:
        """Reject probe fitting during Phase 0."""

        raise NotImplementedError(
            f"{self.contract.probe_id} is {PROBE_PLACEHOLDER_STATUS}; probe fitting belongs to Phase 1."
        )

    train_probe = fit_probe

    def evaluate_probe(self, *_args: Any, **_kwargs: Any) -> None:
        """Reject probe evaluation until feature/probe artifacts exist."""

        raise NotImplementedError(
            f"{self.contract.probe_id} is {PROBE_PLACEHOLDER_STATUS}; no VE probe metrics exist yet."
        )


def default_frozen_encoder_probe_contract(
    *,
    encoder_candidate_id: str = "frozen-encoder-candidate-placeholder",
) -> FrozenEncoderProbeContract:
    """Return the Phase 0 VE probe contract from the canonical evaluation spec."""

    return FrozenEncoderProbeContract(
        probe_id="ve-frozen-encoder-domain-gap-probe-scaffold-v0",
        encoder_candidate_id=encoder_candidate_id,
        feature_source="future deterministic feature cache tied to manifest/config/git_sha",
        task_families=(
            ProbeTaskFamily.MOUSE,
            ProbeTaskFamily.KEYBOARD,
            ProbeTaskFamily.MOUSE_BUTTON,
            ProbeTaskFamily.SCROLL,
            ProbeTaskFamily.CURSOR_CROSSHAIR,
            ProbeTaskFamily.HUD_UI_TEXT,
            ProbeTaskFamily.NEXT_CLICK,
            ProbeTaskFamily.TINY_IDM_TRANSFER,
            ProbeTaskFamily.TINY_FDM_TRANSFER,
        ),
        metric_families=(
            "action_probe_accuracy_or_nll_by_family",
            "screen_state_probe_metric_by_task",
            "per_game_macro_and_held_out_game_macro",
            "long_context_compression_cache_cost",
            "fixed_budget_tiny_idm_tiny_fdm_transfer",
            "feature_extraction_throughput_and_memory",
        ),
        required_aggregations=("micro", "per_game_macro", "held_out_game_macro"),
        evidence_required=(
            "manifest_id",
            "feature_cache_revision",
            "encoder_candidate_revision",
            "git_sha_and_config",
            "probe_train_val_test_split",
            "per_game_and_held_out_metrics",
            "failure_examples_for_hud_ui_cursor_or_crosshair_when_available",
        ),
    )


def frozen_encoder_probe_scaffold(
    *,
    encoder_candidate_id: str = "frozen-encoder-candidate-placeholder",
) -> FrozenEncoderProbeScaffold:
    """Return the default contract-only frozen-encoder probe scaffold."""

    return FrozenEncoderProbeScaffold(default_frozen_encoder_probe_contract(encoder_candidate_id=encoder_candidate_id))


def summarize_probe_contract(contract: FrozenEncoderProbeContract | Mapping[str, Any]) -> dict[str, Any]:
    """Return a compact summary useful for notes/tests."""

    payload = contract.as_dict() if isinstance(contract, FrozenEncoderProbeContract) else dict(contract)
    task_families = tuple(payload.get("task_families", ()))
    return {
        "probe_id": payload.get("probe_id"),
        "status": payload.get("status"),
        "task_family_count": len(task_families),
        "task_families": list(task_families),
        "permits_ve_promotion": bool(payload.get("permits_ve_promotion")),
        "is_trained_probe": bool(payload.get("is_trained_probe")),
    }


__all__ = [
    "PROBE_NO_PROMOTION_CLAIM",
    "PROBE_PLACEHOLDER_STATUS",
    "VE_PROBE_SCAFFOLD_STORY_ID",
    "FrozenEncoderProbeContract",
    "FrozenEncoderProbeScaffold",
    "ProbeTaskFamily",
    "default_frozen_encoder_probe_contract",
    "frozen_encoder_probe_scaffold",
    "summarize_probe_contract",
]
