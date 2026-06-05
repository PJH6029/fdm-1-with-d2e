"""Tables, plots, reports, and failure-analysis contracts; implementation follows later stories."""

from __future__ import annotations

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
    "criterion_ids",
    "draft_fdm1_target_gap_rubric",
    "render_fdm1_target_gap_rubric_markdown",
    "write_fdm1_target_gap_rubric_draft",
]
