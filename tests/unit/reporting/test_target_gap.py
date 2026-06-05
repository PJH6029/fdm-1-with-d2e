from __future__ import annotations

from pathlib import Path

from fdm_1_with_d2e.reporting.target_gap import (
    NON_FINAL_NOTICE,
    TARGET_GAP_RUBRIC_STATUS,
    criterion_ids,
    draft_fdm1_target_gap_rubric,
    render_fdm1_target_gap_rubric_markdown,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RUBRIC_ARTIFACT = REPO_ROOT / "notes/experiments/20260605-phase0-fdm1-target-gap-rubric-draft.md"


def test_target_gap_rubric_is_non_final_and_not_success_claim() -> None:
    rubric = draft_fdm1_target_gap_rubric()
    payload = rubric.as_dict()

    assert payload["status"] == TARGET_GAP_RUBRIC_STATUS
    assert payload["not_success_claim"] is True
    assert NON_FINAL_NOTICE in payload["notes"]
    assert set(payload["source_documents"]) == {
        "docs/reproduction_spec/CANONICAL_SPEC.md",
        "docs/reproduction_spec/spec/evaluation.md",
        "docs/literature_survey/FDM-1.md",
        "docs/literature_survey/D2E.md",
    }
    assert set(criterion_ids(rubric.criteria)) >= {
        "recipe_alignment",
        "causal_input_alignment",
        "d2e_offline_action_quality",
        "pseudo_label_usefulness",
        "logged_free_running_stability",
        "harness_behavior_categories",
        "scale_and_efficiency_gap",
    }
    for criterion in payload["criteria"]:
        assert criterion["current_phase0_status"] == "not_evaluated_phase0_draft_only"
        assert criterion["finality"] == TARGET_GAP_RUBRIC_STATUS
        assert criterion["success_claim_policy"] == "cannot_support_success_claim_without_later_verified_fdm_evidence"
        assert criterion["local_evidence_required"]


def test_target_gap_markdown_and_artifact_carry_non_final_warning() -> None:
    markdown = render_fdm1_target_gap_rubric_markdown()
    artifact = RUBRIC_ARTIFACT.read_text(encoding="utf-8")

    for content in (markdown, artifact):
        assert "Initial FDM-1 target-gap rubric draft (NON-FINAL)" in content
        assert f"Status: `{TARGET_GAP_RUBRIC_STATUS}`" in content
        assert "Not a success claim: `true`" in content
        assert "not a reproduction success claim" in content
        assert "does not evaluate a local FDM" in content
        assert "Phase 0 interpretation" in content
