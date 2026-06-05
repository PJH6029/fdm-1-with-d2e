"""Diagnostic-only IDM/FDM floor scaffold contracts.

These classes are Phase 0 contracts, not trained models.  They make later IDM
and FDM floor paths importable and auditable without implementing any training,
learned inference, checkpoint loading, or quality claim.  Only the floors that
are mathematically deterministic without data fitting (no-op and previous-action
repeat) return predictions; every learned/statistical diagnostic raises an
explicit ``NotImplementedError`` until its later phase implements and verifies it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fdm_1_with_d2e.data.types import (
    ActionBin,
    KeyboardEvent,
    MouseButtonEvent,
    ScrollEvent,
)

FLOOR_SCAFFOLD_STORY_ID = "G006-implement-floor-and-probe-scaffolds"
PLACEHOLDER_STATUS = "diagnostic_placeholder_only_not_trained"
NO_SUCCESS_CLAIM = "floor diagnostic only; never evidence of FDM-1/IDM reproduction success"


class FloorModelFamily(str, Enum):
    """Model family that a diagnostic floor belongs to."""

    IDM = "idm"
    FDM = "fdm"


class FloorKind(str, Enum):
    """Phase 0 floor/scaffold kinds required by the roadmap."""

    NO_OP = "no_op"
    IDM_CE = "idm_ce"
    IDM_MLM = "idm_mlm"
    ACTION_FREQUENCY = "action_frequency"
    PREVIOUS_ACTION = "previous_action"
    ACTION_ONLY = "action_only"
    VIDEO_ONLY = "video_only"


@dataclass(frozen=True, slots=True)
class FloorContract:
    """Serializable description proving a floor is diagnostic-only."""

    floor_id: str
    family: FloorModelFamily
    kind: FloorKind
    label: str
    description: str
    implemented_behavior: str
    later_phase: str
    accepts_video: bool = False
    accepts_action_history: bool = False
    requires_fitted_statistics: bool = False
    requires_later_training: bool = False
    status: str = PLACEHOLDER_STATUS
    diagnostic_only: bool = True
    is_trained_model: bool = False
    permits_success_claim: bool = False
    checkpoint_id: None = None
    created_by_story: str = FLOOR_SCAFFOLD_STORY_ID
    notes: tuple[str, ...] = (NO_SUCCESS_CLAIM,)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly contract record."""

        return {
            "floor_id": self.floor_id,
            "family": self.family.value,
            "kind": self.kind.value,
            "label": self.label,
            "description": self.description,
            "implemented_behavior": self.implemented_behavior,
            "later_phase": self.later_phase,
            "accepts_video": self.accepts_video,
            "accepts_action_history": self.accepts_action_history,
            "requires_fitted_statistics": self.requires_fitted_statistics,
            "requires_later_training": self.requires_later_training,
            "status": self.status,
            "diagnostic_only": self.diagnostic_only,
            "is_trained_model": self.is_trained_model,
            "permits_success_claim": self.permits_success_claim,
            "checkpoint_id": self.checkpoint_id,
            "created_by_story": self.created_by_story,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class FloorPredictionResult:
    """Prediction payload returned only by deterministic diagnostic floors."""

    contract: FloorContract
    predicted_bins: tuple[ActionBin, ...]
    status: str = PLACEHOLDER_STATUS
    deterministic: bool = True
    quality_claim: bool = False
    notes: tuple[str, ...] = field(default_factory=lambda: (NO_SUCCESS_CLAIM,))

    def as_dict(self) -> dict[str, Any]:
        """Return a compact JSON-friendly summary without serializing events."""

        return {
            "floor_id": self.contract.floor_id,
            "family": self.contract.family.value,
            "kind": self.contract.kind.value,
            "status": self.status,
            "deterministic": self.deterministic,
            "quality_claim": self.quality_claim,
            "predicted_bin_count": len(self.predicted_bins),
            "notes": list(self.notes),
        }


class DiagnosticFloorScaffold:
    """Base class for contract-only floor placeholders.

    Subclasses may implement deterministic predictions only when no fitted model,
    checkpoint, or learned inference path is involved.  Training and checkpoint
    APIs deliberately raise so these scaffolds cannot be mistaken for real IDM or
    FDM implementations.
    """

    def __init__(self, contract: FloorContract) -> None:
        self.contract = contract

    @property
    def floor_id(self) -> str:
        return self.contract.floor_id

    @property
    def status(self) -> str:
        return self.contract.status

    @property
    def is_trained_model(self) -> bool:
        return False

    @property
    def permits_success_claim(self) -> bool:
        return False

    def describe(self) -> dict[str, Any]:
        """Return the diagnostic-only floor contract."""

        return self.contract.as_dict()

    def fit(self, *_args: Any, **_kwargs: Any) -> None:
        """Reject training/fitting during Phase 0."""

        raise NotImplementedError(
            f"{self.floor_id} is a {PLACEHOLDER_STATUS} scaffold; fitting/training belongs to "
            f"{self.contract.later_phase} and must produce separate evidence."
        )

    train = fit

    def load_checkpoint(self, *_args: Any, **_kwargs: Any) -> None:
        """Reject checkpoint loading so the scaffold is never a model wrapper."""

        raise NotImplementedError(
            f"{self.floor_id} has no checkpoint surface in Phase 0; it is {PLACEHOLDER_STATUS}."
        )

    def predict_bins(
        self,
        bin_templates: Sequence[ActionBin],
        *,
        context: Mapping[str, Any] | None = None,
    ) -> FloorPredictionResult:
        """Return deterministic diagnostic predictions or raise NotImplemented."""

        raise NotImplementedError(
            f"{self.floor_id} is only an importable contract ({PLACEHOLDER_STATUS}); "
            "learned/statistical prediction is not implemented in Phase 0."
        )


class NoOpFloorScaffold(DiagnosticFloorScaffold):
    """Deterministic zero-mouse/no-sparse-event diagnostic floor."""

    def predict_bins(
        self,
        bin_templates: Sequence[ActionBin],
        *,
        context: Mapping[str, Any] | None = None,
    ) -> FloorPredictionResult:
        del context
        predictions = tuple(no_op_bin_from_template(template) for template in bin_templates)
        return FloorPredictionResult(
            contract=self.contract,
            predicted_bins=predictions,
            notes=(
                NO_SUCCESS_CLAIM,
                "Deterministic zero-mouse/no-sparse-event output for metric floor sanity checks only.",
            ),
        )


class PreviousActionFloorScaffold(DiagnosticFloorScaffold):
    """Deterministic FDM previous-action repeat diagnostic floor."""

    def predict_bins(
        self,
        bin_templates: Sequence[ActionBin],
        *,
        context: Mapping[str, Any] | None = None,
    ) -> FloorPredictionResult:
        context = context or {}
        previous_action = _resolve_previous_action(context)
        predictions: list[ActionBin] = []
        fallback_used = previous_action is None

        for template in bin_templates:
            if previous_action is None:
                predicted = no_op_bin_from_template(template)
            else:
                predicted = repeat_action_into_template(previous_action, template)
            predictions.append(predicted)
            previous_action = predicted

        notes = [
            NO_SUCCESS_CLAIM,
            "Deterministic previous-action repeat floor; no video understanding or trained FDM is involved.",
        ]
        if fallback_used:
            notes.append("No previous action was supplied; the first prediction falls back to no-op.")

        return FloorPredictionResult(contract=self.contract, predicted_bins=tuple(predictions), notes=tuple(notes))


class ActionFrequencyFloorScaffold(DiagnosticFloorScaffold):
    """Contract for a future action-frequency prior floor.

    Phase 0 intentionally does not fit or infer from frequencies. Later phases
    must supply a frozen action-distribution artifact and tests before this can
    produce deterministic diagnostic outputs.
    """

    def predict_bins(
        self,
        bin_templates: Sequence[ActionBin],
        *,
        context: Mapping[str, Any] | None = None,
    ) -> FloorPredictionResult:
        del bin_templates, context
        raise NotImplementedError(
            f"{self.floor_id} requires a verified frozen action-distribution artifact; "
            f"Phase 0 exposes only the {PLACEHOLDER_STATUS} contract."
        )


class IDMObjectiveDiagnosticScaffold(DiagnosticFloorScaffold):
    """Contract for a future IDM objective diagnostic such as CE or MLM."""

    def predict_bins(
        self,
        bin_templates: Sequence[ActionBin],
        *,
        context: Mapping[str, Any] | None = None,
    ) -> FloorPredictionResult:
        del bin_templates, context
        raise NotImplementedError(
            f"{self.floor_id} is a later IDM objective diagnostic requiring implemented video/action features "
            f"and training; Phase 0 exposes only the {PLACEHOLDER_STATUS} contract."
        )


class ActionOnlyFloorScaffold(DiagnosticFloorScaffold):
    """Contract for a future FDM action-history-only transformer diagnostic."""

    def predict_bins(
        self,
        bin_templates: Sequence[ActionBin],
        *,
        context: Mapping[str, Any] | None = None,
    ) -> FloorPredictionResult:
        del bin_templates, context
        raise NotImplementedError(
            f"{self.floor_id} is a later FDM diagnostic requiring an implemented action-only model; "
            f"Phase 0 exposes only the {PLACEHOLDER_STATUS} contract."
        )


class VideoOnlyFloorScaffold(DiagnosticFloorScaffold):
    """Contract for a future FDM video-only transformer diagnostic."""

    def predict_bins(
        self,
        bin_templates: Sequence[ActionBin],
        *,
        context: Mapping[str, Any] | None = None,
    ) -> FloorPredictionResult:
        del bin_templates, context
        raise NotImplementedError(
            f"{self.floor_id} is a later FDM diagnostic requiring implemented video features/modeling; "
            f"Phase 0 exposes only the {PLACEHOLDER_STATUS} contract."
        )


def idm_no_op_floor() -> NoOpFloorScaffold:
    """Return the IDM no-op/zero-mouse sanity floor contract."""

    return NoOpFloorScaffold(
        FloorContract(
            floor_id="idm-no-op-zero-mouse-floor-v0",
            family=FloorModelFamily.IDM,
            kind=FloorKind.NO_OP,
            label="IDM no-op / zero-mouse sanity floor",
            description="Predicts no sparse events and zero mouse movement for every 50ms target bin.",
            implemented_behavior="deterministic_zero_mouse_no_sparse_events",
            later_phase="Phase 2 IDM diagnostics",
        )
    )


def idm_action_frequency_floor() -> ActionFrequencyFloorScaffold:
    """Return the IDM action-frequency prior contract."""

    return ActionFrequencyFloorScaffold(
        FloorContract(
            floor_id="idm-action-frequency-floor-v0",
            family=FloorModelFamily.IDM,
            kind=FloorKind.ACTION_FREQUENCY,
            label="IDM action-frequency prior sanity floor",
            description="Later diagnostic prior that predicts from a frozen train-split action distribution.",
            implemented_behavior="not_implemented_until_verified_frequency_artifact",
            later_phase="Phase 2 IDM diagnostics",
            requires_fitted_statistics=True,
        )
    )


def idm_ce_floor() -> IDMObjectiveDiagnosticScaffold:
    """Return the IDM-CE one-shot classifier diagnostic contract."""

    return IDMObjectiveDiagnosticScaffold(
        FloorContract(
            floor_id="idm-ce-one-shot-classifier-diagnostic-v0",
            family=FloorModelFamily.IDM,
            kind=FloorKind.IDM_CE,
            label="IDM-CE one-shot classifier diagnostic",
            description="Later non-causal classifier floor over target action slots; Phase 0 only exposes the diagnostic contract.",
            implemented_behavior="not_implemented_until_later_idm_diagnostic_model",
            later_phase="Phase 2 IDM diagnostics",
            accepts_video=True,
            requires_later_training=True,
        )
    )


def idm_mlm_floor() -> IDMObjectiveDiagnosticScaffold:
    """Return the IDM-MLM random-mask denoising diagnostic contract."""

    return IDMObjectiveDiagnosticScaffold(
        FloorContract(
            floor_id="idm-mlm-random-mask-denoising-diagnostic-v0",
            family=FloorModelFamily.IDM,
            kind=FloorKind.IDM_MLM,
            label="IDM-MLM random-mask denoising diagnostic",
            description="Later random-mask denoising floor for isolating diffusion-schedule value; Phase 0 only exposes the diagnostic contract.",
            implemented_behavior="not_implemented_until_later_idm_diagnostic_model",
            later_phase="Phase 2 IDM diagnostics",
            accepts_video=True,
            accepts_action_history=True,
            requires_later_training=True,
        )
    )


def fdm_no_op_floor() -> NoOpFloorScaffold:
    """Return the FDM-B0 no-op/zero-mouse floor contract."""

    return NoOpFloorScaffold(
        FloorContract(
            floor_id="fdm-b0-no-op-zero-mouse-floor-v0",
            family=FloorModelFamily.FDM,
            kind=FloorKind.NO_OP,
            label="FDM-B0 no-op / zero-mouse floor",
            description="Predicts no sparse events and zero mouse movement for causal FDM metric floor checks.",
            implemented_behavior="deterministic_zero_mouse_no_sparse_events",
            later_phase="Phase 4 FDM floor diagnostics",
        )
    )


def fdm_previous_action_floor() -> PreviousActionFloorScaffold:
    """Return the FDM-B1 previous-action repeat floor contract."""

    return PreviousActionFloorScaffold(
        FloorContract(
            floor_id="fdm-b1-previous-action-repeat-floor-v0",
            family=FloorModelFamily.FDM,
            kind=FloorKind.PREVIOUS_ACTION,
            label="FDM-B1 previous-action repeat floor",
            description="Repeats the previous action bin into each requested target bin without using future visuals.",
            implemented_behavior="deterministic_previous_action_repeat_with_no_op_fallback",
            later_phase="Phase 4 FDM floor diagnostics",
            accepts_action_history=True,
        )
    )


def fdm_action_only_floor() -> ActionOnlyFloorScaffold:
    """Return the FDM-B2 action-history-only diagnostic contract."""

    return ActionOnlyFloorScaffold(
        FloorContract(
            floor_id="fdm-b2-action-only-diagnostic-v0",
            family=FloorModelFamily.FDM,
            kind=FloorKind.ACTION_ONLY,
            label="FDM-B2 action-only transformer diagnostic",
            description="Later diagnostic that predicts from prior actions only, with video excluded.",
            implemented_behavior="not_implemented_until_later_fdm_diagnostic_model",
            later_phase="Phase 4 FDM floor diagnostics",
            accepts_action_history=True,
            requires_later_training=True,
        )
    )


def fdm_video_only_floor() -> VideoOnlyFloorScaffold:
    """Return the FDM-B3 video-only diagnostic contract."""

    return VideoOnlyFloorScaffold(
        FloorContract(
            floor_id="fdm-b3-video-only-diagnostic-v0",
            family=FloorModelFamily.FDM,
            kind=FloorKind.VIDEO_ONLY,
            label="FDM-B3 video-only transformer diagnostic",
            description="Later diagnostic that predicts from causal video tokens only, with prior actions excluded.",
            implemented_behavior="not_implemented_until_later_fdm_diagnostic_model",
            later_phase="Phase 4 FDM floor diagnostics",
            accepts_video=True,
            requires_later_training=True,
        )
    )


def all_floor_scaffolds() -> tuple[DiagnosticFloorScaffold, ...]:
    """Return all Phase 0 importable floor scaffold instances."""

    return (
        idm_no_op_floor(),
        idm_action_frequency_floor(),
        idm_ce_floor(),
        idm_mlm_floor(),
        fdm_no_op_floor(),
        fdm_previous_action_floor(),
        fdm_action_only_floor(),
        fdm_video_only_floor(),
    )


def all_floor_contracts() -> tuple[FloorContract, ...]:
    """Return all Phase 0 floor contracts."""

    return tuple(scaffold.contract for scaffold in all_floor_scaffolds())


def no_op_bin_from_template(template: ActionBin) -> ActionBin:
    """Create a zero-mouse/no-event bin preserving index and interval."""

    return ActionBin(index=template.index, start_ns=template.start_ns, end_ns=template.end_ns)


def repeat_action_into_template(source: ActionBin, template: ActionBin) -> ActionBin:
    """Copy source action content into a target interval deterministically.

    Sparse event kinds and values are preserved while timestamps are shifted by
    each event's offset from ``source.start_ns`` and clamped into the half-open
    target bin. This is a diagnostic repeat rule, not a learned FDM rollout.
    """

    return ActionBin(
        index=template.index,
        start_ns=template.start_ns,
        end_ns=template.end_ns,
        mouse_dx=source.mouse_dx,
        mouse_dy=source.mouse_dy,
        keyboard_events=tuple(_copy_keyboard_event(event, source, template) for event in source.keyboard_events),
        mouse_button_events=tuple(
            _copy_mouse_button_event(event, source, template) for event in source.mouse_button_events
        ),
        scroll_events=tuple(_copy_scroll_event(event, source, template) for event in source.scroll_events),
    )


def _resolve_previous_action(context: Mapping[str, Any]) -> ActionBin | None:
    previous_action = context.get("previous_action")
    if isinstance(previous_action, ActionBin):
        return previous_action

    history = context.get("action_history") or context.get("previous_action_bins")
    if isinstance(history, Sequence) and history:
        candidate = history[-1]
        if isinstance(candidate, ActionBin):
            return candidate
    return None


def _shift_timestamp(timestamp_ns: int, source: ActionBin, template: ActionBin) -> int:
    source_duration = max(1, source.end_ns - source.start_ns)
    target_duration = max(1, template.end_ns - template.start_ns)
    offset = timestamp_ns - source.start_ns
    offset = max(0, min(source_duration - 1, offset))
    if source_duration != target_duration:
        offset = round(offset * target_duration / source_duration)
    offset = max(0, min(target_duration - 1, offset))
    return template.start_ns + offset


def _copy_keyboard_event(event: KeyboardEvent, source: ActionBin, template: ActionBin) -> KeyboardEvent:
    return KeyboardEvent(
        timestamp_ns=_shift_timestamp(event.timestamp_ns, source, template),
        key=event.key,
        event_type=event.event_type,
    )


def _copy_mouse_button_event(event: MouseButtonEvent, source: ActionBin, template: ActionBin) -> MouseButtonEvent:
    return MouseButtonEvent(
        timestamp_ns=_shift_timestamp(event.timestamp_ns, source, template),
        button=event.button,
        event_type=event.event_type,
    )


def _copy_scroll_event(event: ScrollEvent, source: ActionBin, template: ActionBin) -> ScrollEvent:
    return ScrollEvent(
        timestamp_ns=_shift_timestamp(event.timestamp_ns, source, template),
        delta_x=event.delta_x,
        delta_y=event.delta_y,
    )


__all__ = [
    "ActionFrequencyFloorScaffold",
    "ActionOnlyFloorScaffold",
    "DiagnosticFloorScaffold",
    "FLOOR_SCAFFOLD_STORY_ID",
    "FloorContract",
    "FloorKind",
    "FloorModelFamily",
    "FloorPredictionResult",
    "IDMObjectiveDiagnosticScaffold",
    "NO_SUCCESS_CLAIM",
    "NoOpFloorScaffold",
    "PLACEHOLDER_STATUS",
    "PreviousActionFloorScaffold",
    "VideoOnlyFloorScaffold",
    "all_floor_contracts",
    "all_floor_scaffolds",
    "fdm_action_only_floor",
    "fdm_no_op_floor",
    "fdm_previous_action_floor",
    "fdm_video_only_floor",
    "idm_action_frequency_floor",
    "idm_ce_floor",
    "idm_mlm_floor",
    "idm_no_op_floor",
    "no_op_bin_from_template",
    "repeat_action_into_template",
]
