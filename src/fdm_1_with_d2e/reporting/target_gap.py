"""Non-final FDM-1 target-gap rubric draft helpers.

The rubric describes evidence categories for comparing later local FDM runs to
public FDM-1 claims where direct checkpoint/evaluator comparison is impossible.
It is intentionally labeled as a draft and must not be interpreted as a success
claim or final threshold set.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TARGET_GAP_STORY_ID = "G006-implement-floor-and-probe-scaffolds"
TARGET_GAP_RUBRIC_STATUS = "non_final_draft_no_success_claim"
TARGET_GAP_RUBRIC_VERSION = "phase0-fdm1-target-gap-rubric-draft-v0"
NON_FINAL_NOTICE = (
    "NON-FINAL DRAFT: this rubric is not a reproduction success claim, not a trained-model "
    "evaluation, and not a replacement for later FDM/free-running/harness evidence."
)


@dataclass(frozen=True, slots=True)
class TargetGapCriterion:
    """One draft target-gap evidence criterion."""

    criterion_id: str
    category: str
    question: str
    public_or_spec_basis: str
    local_evidence_required: tuple[str, ...]
    current_phase0_status: str = "not_evaluated_phase0_draft_only"
    finality: str = TARGET_GAP_RUBRIC_STATUS
    success_claim_policy: str = "cannot_support_success_claim_without_later_verified_fdm_evidence"

    def as_dict(self) -> dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "category": self.category,
            "question": self.question,
            "public_or_spec_basis": self.public_or_spec_basis,
            "local_evidence_required": list(self.local_evidence_required),
            "current_phase0_status": self.current_phase0_status,
            "finality": self.finality,
            "success_claim_policy": self.success_claim_policy,
        }


@dataclass(frozen=True, slots=True)
class TargetGapRubric:
    """Draft FDM-1 target-gap rubric with explicit non-final status."""

    rubric_id: str
    title: str
    status: str
    created_by_story: str
    criteria: tuple[TargetGapCriterion, ...]
    source_documents: tuple[str, ...]
    not_success_claim: bool = True
    notes: tuple[str, ...] = (NON_FINAL_NOTICE,)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rubric_id": self.rubric_id,
            "title": self.title,
            "status": self.status,
            "created_by_story": self.created_by_story,
            "not_success_claim": self.not_success_claim,
            "source_documents": list(self.source_documents),
            "criteria": [criterion.as_dict() for criterion in self.criteria],
            "notes": list(self.notes),
        }

    def to_markdown(self) -> str:
        """Render a stable markdown artifact for notes/experiments."""

        lines = [
            f"# {self.title}",
            "",
            f"Rubric id: `{self.rubric_id}`",
            f"Status: `{self.status}`",
            f"Created by story: `{self.created_by_story}`",
            f"Not a success claim: `{str(self.not_success_claim).lower()}`",
            "",
            f"**{NON_FINAL_NOTICE}**",
            "",
            "## Source basis",
            "",
        ]
        lines.extend(f"- `{document}`" for document in self.source_documents)
        lines.extend(["", "## Draft criteria", ""])
        for index, criterion in enumerate(self.criteria, start=1):
            lines.extend(
                [
                    f"### {index}. {criterion.category}",
                    "",
                    f"- Criterion id: `{criterion.criterion_id}`",
                    f"- Question: {criterion.question}",
                    f"- Public/spec basis: {criterion.public_or_spec_basis}",
                    f"- Current status: `{criterion.current_phase0_status}`",
                    f"- Finality: `{criterion.finality}`",
                    f"- Success-claim policy: `{criterion.success_claim_policy}`",
                    "- Local evidence required:",
                ]
            )
            lines.extend(f"  - {item}" for item in criterion.local_evidence_required)
            lines.append("")
        lines.extend(
            [
                "## Phase 0 interpretation",
                "",
                "This artifact only fixes the vocabulary of later target-gap evidence. It does not evaluate a local FDM,",
                "does not compare against the closed-source FDM-1 checkpoint, and does not complete any Phase 4/6 success gate.",
                "Later reports must replace `not_evaluated_phase0_draft_only` entries with run-record-backed metrics,",
                "failure cases, and explicit non-comparable gaps.",
                "",
            ]
        )
        return "\n".join(lines)


def draft_fdm1_target_gap_rubric() -> TargetGapRubric:
    """Return the initial non-final FDM-1 target-gap rubric draft."""

    return TargetGapRubric(
        rubric_id=TARGET_GAP_RUBRIC_VERSION,
        title="Initial FDM-1 target-gap rubric draft (NON-FINAL)",
        status=TARGET_GAP_RUBRIC_STATUS,
        created_by_story=TARGET_GAP_STORY_ID,
        source_documents=(
            "docs/reproduction_spec/CANONICAL_SPEC.md",
            "docs/reproduction_spec/spec/evaluation.md",
            "docs/literature_survey/FDM-1.md",
            "docs/literature_survey/D2E.md",
        ),
        criteria=(
            TargetGapCriterion(
                criterion_id="recipe_alignment",
                category="Public recipe and action-token alignment",
                question="Does the local FDM training path match the public VE -> IDM pseudo-labeling -> FDM recipe and action-token semantics closely enough to compare gaps?",
                public_or_spec_basis="Public/local spec describes interleaved video/action FDM training on IDM-labeled videos, keyboard press/release, scroll, 49x49 mouse bins, no-op handling, and optional next-click evidence.",
                local_evidence_required=(
                    "Committed tokenizer/action-vocab revision and prediction-to-event conversion revision.",
                    "Run record showing GT/pseudo/filtered-pseudo/mix data source for each FDM checkpoint.",
                    "Explicit list of unmatched public ingredients such as transcripts/language grounding or private corpus scale.",
                ),
            ),
            TargetGapCriterion(
                criterion_id="causal_input_alignment",
                category="Causal FDM input alignment",
                question="Does the FDM predict action bin [t,t+50ms) without visual evidence after decision time t?",
                public_or_spec_basis="Canonical FDM spec requires strict no-future-visual alignment before any FDM metric can be trusted.",
                local_evidence_required=(
                    "No-future-visual leakage guard test for the chosen visual-bin indexing policy.",
                    "Feature-cache metadata showing source frame span, decision time, and causal-safety flag.",
                    "Failure note if any model used target-interval or future frames.",
                ),
            ),
            TargetGapCriterion(
                criterion_id="d2e_offline_action_quality",
                category="D2E offline action quality against floor diagnostics",
                question="Does a trained FDM beat no-op, previous-action, action-only, and video-only diagnostics on reproducible D2E action metrics without hiding per-game regressions?",
                public_or_spec_basis="D2E evaluation uses non-overlapping 50ms bins with mouse Pearson/scale and keyboard/mouse-button accuracy; FDM spec adds NLL, sparse F1, and no-op FP/FN.",
                local_evidence_required=(
                    "Teacher-forced NLL/CE by token family.",
                    "D2E-style action metrics after prediction-to-event/MCAP-compatible conversion.",
                    "Sparse event precision/recall/F1, no-op FP/FN, per-game macro, held-out-game macro, and floor-baseline comparisons.",
                ),
            ),
            TargetGapCriterion(
                criterion_id="pseudo_label_usefulness",
                category="Pseudo-label usefulness",
                question="Do IDM pseudo-labels retain useful FDM performance relative to GT labels, and does filtering improve quality/coverage?",
                public_or_spec_basis="The public recipe trains FDM on IDM-labeled videos; canonical spec requires FDM-GT, FDM-Pseudo, FDM-FilteredPseudo, and FDM-Mix comparisons.",
                local_evidence_required=(
                    "FDM-Pseudo/FDM-FilteredPseudo/FDM-Mix metrics relative to FDM-GT on the same split/budget.",
                    "Pseudo-label confidence/coverage curves and no-op/event-rate drift.",
                    "Filtering threshold and low-confidence handling run records.",
                ),
            ),
            TargetGapCriterion(
                criterion_id="logged_free_running_stability",
                category="Logged free-running stability",
                question="When predicted previous actions are fed back while logged video is fixed, does behavior remain stable over horizon?",
                public_or_spec_basis="Evaluation spec requires free-running degradation, action spam, no-op collapse, key/button violations, and mouse drift before final FDM claims.",
                local_evidence_required=(
                    "Per-horizon degradation curves using predicted previous actions.",
                    "No-op collapse/action-spam rates, key/button state violations, mouse drift, and representative failure clips/logs.",
                    "Comparison to floor diagnostics under identical replay-control conditions.",
                ),
            ),
            TargetGapCriterion(
                criterion_id="harness_behavior_categories",
                category="Comparable harness behavior categories",
                question="Where local desktop/game or replay-control harness scenarios overlap public FDM-1 behavior categories, what succeeds, fails, or remains non-comparable?",
                public_or_spec_basis="The FDM-1 survey records public/post-aligned categories including Typing Test, Verbal Memory, Symbolic Memory, and Target Accuracy; canonical spec requires stable harness behavior.",
                local_evidence_required=(
                    "Scenario definitions, seeds, run duration, action count/rate, invalid actions, stuck states, drift/explosion, crash/hang, and simple task/sanity success.",
                    "Category-level mapping table explaining which public categories are comparable locally.",
                    "Failure analysis for UI/text/cursor/crosshair or game-state perception issues.",
                ),
            ),
            TargetGapCriterion(
                criterion_id="scale_and_efficiency_gap",
                category="Data/model scale and efficiency gap",
                question="How much of the remaining gap is explained by D2E data scale, model scale, context length, VE compression, and throughput?",
                public_or_spec_basis="Canonical spec says the closed FDM-1 data/model/eval details are unavailable and warns against claiming parity with private-scale systems without direct evidence.",
                local_evidence_required=(
                    "IDM/FDM scaling curves at required D2E scales and selected optional low-scale points.",
                    "Model parameter count, context length, feature-cache cost, GPU throughput, and inference latency records.",
                    "Explicit non-comparable gap list for private data, model details, transcripts/language grounding, and closed harness/evaluator differences.",
                ),
            ),
        ),
    )


def render_fdm1_target_gap_rubric_markdown() -> str:
    """Render the initial target-gap rubric draft as markdown."""

    return draft_fdm1_target_gap_rubric().to_markdown()


def write_fdm1_target_gap_rubric_draft(path: str | Path) -> Path:
    """Write the non-final draft rubric artifact and return its path."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_fdm1_target_gap_rubric_markdown(), encoding="utf-8")
    return output_path


def criterion_ids(criteria: Sequence[TargetGapCriterion] | None = None) -> tuple[str, ...]:
    """Return stable criterion ids for tests/reporting."""

    selected = tuple(criteria) if criteria is not None else draft_fdm1_target_gap_rubric().criteria
    return tuple(criterion.criterion_id for criterion in selected)


__all__ = [
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
