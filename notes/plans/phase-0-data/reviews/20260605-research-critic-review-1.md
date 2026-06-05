# Research Critic review 1 — Phase 0 data foundation

**Verdict:** `APPROVE`

**Justification:** The revised Phase 0 plan is suitable as an Ultragoal brief. It integrates the Research Architect's blocking fixes: real-D2E/MLXP exit evidence, official evaluator invocation or deviation table, offline default tests, target-gap rubric artifact, and operational run-record constraints.

## Gate checks

- Evidence integration: PASS — Uses Phase 0 roadmap/specs, D2E/FDM-1 surveys, and verified upstream D2E references.
- Primary-source/local verification: PASS — D2E HEAD, README, `evaluate.py`, `inference.py`, and Hugging Face paths were checked; local spec paths exist.
- Spec conflict handling: PASS — Keeps Phase 0 separate from Phase 0.5 and marks floor/scaffold outputs as placeholders only.
- Success/failure gates: PASS — Gates are measurable, including pytest, real-D2E MLXP smoke, overflow threshold, official evaluator/deviation, and GPT-Pro phase-exit review.
- Ablation realism/value: PASS — Correctly treats Phase 0 as test/evidence-based rather than model-quality ablation.
- Operational compliance: PASS — Uses `uv`, read-only dataset handling, commit/push before MLXP, immutable image/digest, artifact paths, pod cancellation, and W&B only where appropriate.
- ROADMAP/DECISIONS hygiene: PASS — Uses them as checklist/register inputs and defers updates until concrete evidence.
- Ultragoal readiness: PASS — Work is decomposed into bounded, disjoint implementation stories with clear exit evidence.

## Required changes

None blocking. When converting to Ultragoal, preserve the real-D2E/MLXP evidence story and official evaluator/deviation-table story as mandatory terminal checks.

## Evidence references

- `notes/plans/phase-0-data/20260605-data-foundation-plan.md`: revised plan with required real-D2E checks, success gates, cluster plan, and decision slots.
- `notes/plans/phase-0-data/reviews/20260605-research-architect-review-1.md`: architect requested revisions; plan now addresses them.
- `docs/reproduction_spec/ROADMAP.md`: Phase 0 checklist matches planned deliverables.
- `docs/reproduction_spec/CANONICAL_SPEC.md`: Gate 0 and data/action requirements.
- `docs/reproduction_spec/spec/data_and_actions.md`: 50ms bins, `K=8`, tokenization, overflow policy.
- `docs/reproduction_spec/spec/evaluation.md`: official evaluator preference and deviation-recording rule.
- `docs/reproduction_spec/OPERATIONAL_RULES.md`: MLXP, dataset, image, artifact, and W&B constraints.
- `https://github.com/worv-ai/D2E/tree/80e98e26e4dc584ec76fec5789b4a97c275dd032`: upstream D2E revision used by the plan.
- `https://huggingface.co/open-world-agents/Generalist-IDM-1B` and `https://huggingface.co/datasets/open-world-agents/D2E-480p`: reference model/dataset paths exist.
