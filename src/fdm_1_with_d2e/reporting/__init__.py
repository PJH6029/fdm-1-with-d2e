"""Tables, plots, reports, and failure-analysis contracts; implementation follows later stories."""

from __future__ import annotations


from fdm_1_with_d2e.reporting.overflow_stats import (
    DEFAULT_K_SWEEP,
    OVERFLOW_STATS_SCHEMA,
    OVERFLOW_STATS_STORY_ID,
    aggregate_recording_summaries,
    sparse_candidate_tokens,
    summarize_dataset_overflow,
    summarize_overflow_for_bins,
    token_family_label,
)
from fdm_1_with_d2e.reporting.temporal_sanity import (
    TEMPORAL_SANITY_SCHEMA,
    TEMPORAL_SANITY_STORY_ID,
    TemporalWindowSelection,
    bins_for_screen_span,
    export_temporal_sanity_window,
    replay_keyboard_state,
    resolve_window_selection,
)

from fdm_1_with_d2e.reporting.target_gap import (
    NON_FINAL_NOTICE,
    TARGET_GAP_RUBRIC_STATUS,
    TARGET_GAP_RUBRIC_VERSION,
    TARGET_GAP_STORY_ID,
    TargetGapCriterion,
    TargetGapRubric,
    criterion_ids,
    draft_fdm1_target_gap_rubric,
    render_fdm1_target_gap_rubric_markdown,
    write_fdm1_target_gap_rubric_draft,
)

BOOTSTRAP_STATUS = "placeholder_contract_only"

__all__ = [
    "BOOTSTRAP_STATUS",
    "NON_FINAL_NOTICE",
    "TARGET_GAP_RUBRIC_STATUS",
    "TARGET_GAP_RUBRIC_VERSION",
    "TARGET_GAP_STORY_ID",
    "TargetGapCriterion",
    "TargetGapRubric",
    "DEFAULT_K_SWEEP",
    "OVERFLOW_STATS_SCHEMA",
    "OVERFLOW_STATS_STORY_ID",
    "TEMPORAL_SANITY_SCHEMA",
    "TEMPORAL_SANITY_STORY_ID",
    "TemporalWindowSelection",
    "aggregate_recording_summaries",
    "bins_for_screen_span",
    "export_temporal_sanity_window",
    "replay_keyboard_state",
    "resolve_window_selection",
    "sparse_candidate_tokens",
    "summarize_dataset_overflow",
    "summarize_overflow_for_bins",
    "token_family_label",
    "criterion_ids",
    "draft_fdm1_target_gap_rubric",
    "render_fdm1_target_gap_rubric_markdown",
    "write_fdm1_target_gap_rubric_draft",
]
