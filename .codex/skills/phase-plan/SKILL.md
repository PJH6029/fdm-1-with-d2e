---
name: phase-plan
description: 'Use in this FDM-1/D2E repo to create or quality-control a phase-level research/directional plan under notes/plans/phase-* before Ultragoal execution. Use after GPT-Pro/literature review and before ultragoal for each ROADMAP phase; returns APPROVE, REVISE, or ESCALATE_TO_RALPLAN without writing ROADMAP.md or DECISIONS.md.'
---

# Phase Plan

Create and review phase-level research briefs for the FDM-1/D2E reproduction loop. This skill is lighter than `$ralplan`: it decides the research direction for a ROADMAP phase, not the implementation-ready PRD/test-spec handoff.

## Artifact boundary

`notes/plans/phase-*` plans are **research/phase directional plans**. They should include:

- current spec/evidence summary;
- GPT-Pro and literature artifact links;
- agent interpretation, hypotheses, and known uncertainty;
- high-level implementation direction;
- ablation/evaluation direction;
- MLXP cluster/resource plan;
- staged judgments that must not be copied into `ROADMAP.md` or `DECISIONS.md` before implementation or experiment evidence exists.

`$ralplan` artifacts are **implementation-focused consensus handoffs**. They belong under `.omx/plans/` and should include PRD/test-spec/ADR, concrete acceptance criteria, Architect -> Critic approval, and an execution-ready plan for `$ultragoal`, `$team`, or `$ralph`.

If escalation to `$ralplan` is needed, keep the phase plan as a thin index/brief: why ralplan is needed, which GPT-Pro/literature evidence should be fed into it, and where the resulting `.omx/plans/` artifact lives. Do not duplicate PRD/test-spec content in `notes/plans/phase-*`.

## Workflow

1. Inspect the selected `docs/reproduction_spec/ROADMAP.md` phase, `CANONICAL_SPEC.md`, component specs, existing `docs/literature_survey/`, current evidence, and relevant GPT-Pro artifacts.
2. Draft or update a phase plan at `notes/plans/phase-<n>-<name>/YYYYMMDD-<topic>-plan.md`.
3. Run review before Ultragoal creation:
   - Prefer the repo-local `research-architect` native subagent first for phase-direction soundness, hidden coupling, method plausibility, and feasibility.
   - Then launch the repo-local `research-critic` native subagent with the draft and Research Architect review; the Research Critic must return exactly one verdict: `APPROVE`, `REVISE`, or `ESCALATE_TO_RALPLAN`.
   - Do not run the Architect and Critic reviews in parallel; preserve the Architect -> Critic sequence.
   - `research-architect` and `research-critic` are repo-local agents under `.codex/agents/` and are intentionally configured with `model = "gpt-5.5"` and `model_reasoning_effort = "xhigh"`. If the current runtime cannot discover project-local native agents until session reload, fall back to installed `architect` then `critic`, and record the degraded reviewer setting in the phase plan review result.
4. If verdict is `REVISE`, update the phase plan and repeat review. Limit routine re-review to 5 loops before escalating or reporting the blocker.
5. If verdict is `APPROVE`, use the phase plan as the Ultragoal brief input.
6. If verdict is `ESCALATE_TO_RALPLAN`, run `$ralplan --deliberate` with the phase plan, Architect review, Critic verdict, and relevant GPT-Pro/literature artifacts as context. After consensus, update the phase plan only as a thin index to the ralplan artifact.

## Plan template

```markdown
# Phase plan: <phase/topic>

## Scope
## Current spec/evidence
## Literature and GPT-Pro artifacts used
## Agent interpretation and hypotheses
## Proposed implementation direction
## Proposed experiment / ablation matrix
## Success gate
## Failure / fallback criteria
## Cluster execution plan
## Review result
- Research Architect review: <summary or artifact path>
- Research Critic verdict: APPROVE | REVISE | ESCALATE_TO_RALPLAN
- Ralplan escalation: <none or .omx/plans/... path>
## Decision slots to fill after evidence
```

## Review criteria

The Research Architect and Research Critic must check:

- GPT-Pro/literature evidence is reflected in the plan;
- GPT-Pro claims are not accepted without primary-source or local-evidence verification;
- conflicts with current specs are explicit;
- success and failure gates are measurable;
- ablation matrix is research-useful and operationally realistic;
- MLXP/GPU/data/W&B rules are respected;
- `ROADMAP.md` and `DECISIONS.md` are not used as pre-implementation logs;
- the plan is either ready to become an Ultragoal brief or requires `$ralplan --deliberate`.

## Verdict meanings

- `APPROVE`: The phase plan is suitable as an Ultragoal brief.
- `REVISE`: The phase plan has fixable gaps; revise and re-review.
- `ESCALATE_TO_RALPLAN`: Architecture, objective, training recipe, evaluation, or operational risk is high enough to require consensus planning before Ultragoal.

## Guardrails

- Do not modify `ROADMAP.md` or `DECISIONS.md` while drafting or reviewing the phase plan.
- Do not use phase plan approval as phase progress evidence. Progress requires implementation, run, or verification artifacts.
- Do not let GPT-Pro decide alone; the plan must state how external recommendations were verified, adopted, deferred, or rejected.
- Do not start `$ralph` from a phase plan unless an Ultragoal story or ralplan handoff already gives a concrete execute/test scope.
