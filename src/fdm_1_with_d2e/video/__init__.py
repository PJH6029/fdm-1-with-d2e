"""Video encoder, feature-cache, sampler, and probe contracts; implementation follows later stories."""

from __future__ import annotations

from fdm_1_with_d2e.video.scaffold import (
    PROBE_NO_PROMOTION_CLAIM,
    PROBE_PLACEHOLDER_STATUS,
    VE_PROBE_SCAFFOLD_STORY_ID,
    FrozenEncoderProbeContract,
    FrozenEncoderProbeScaffold,
    ProbeTaskFamily,
    default_frozen_encoder_probe_contract,
    frozen_encoder_probe_scaffold,
    summarize_probe_contract,
)

BOOTSTRAP_STATUS = "placeholder_contract_only"

__all__ = [
    "BOOTSTRAP_STATUS",
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
