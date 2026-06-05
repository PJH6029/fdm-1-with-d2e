---
name: reproduction-phase-loop
description: 'Use for each docs/reproduction_spec/ROADMAP.md phase in this FDM-1/D2E repo to run the autonomous research loop: inspect spec/evidence, use GPT-Pro gates, run phase-plan quality control, escalate to ralplan when risk is material, create a mandatory ultragoal ledger, delegate execution to research-executor or team, and update ROADMAP.md/DECISIONS.md only after implementation or experiment evidence exists.'
---

# Reproduction Phase Loop

Drive one `ROADMAP.md` phase from research uncertainty to phase-exit evidence. This repo-local skill is the lifecycle supervisor over `$gpt-pro-query`, `$phase-plan`, optional `$ralplan`, `$ultragoal`, native `research-executor`, and `$team`; it does not replace those engines.

## One-screen contract

Core structure:
```text
$reproduction-phase-loop
  ├─ inspect local spec/evidence
  ├─ $gpt-pro-query when gated
  ├─ $phase-plan
  │    └─ research-architect -> research-critic
  ├─ optional $ralplan --deliberate
  ├─ mandatory $ultragoal
  │    ├─ implementation stories
  │    ├─ operational preflight story before MLXP runs
  │    ├─ evaluation stories
  │    ├─ phase-exit GPT-Pro review story
  │    └─ ROADMAP/DECISIONS update story
  └─ execution lane
       ├─ native research-executor subagent
       └─ $team
```

Canonical path:

```text
inspect spec/evidence
-> gated $gpt-pro-query
-> $phase-plan (research-architect -> research-critic)
-> optional $ralplan --deliberate on ESCALATE_TO_RALPLAN or material risk
-> mandatory $ultragoal phase ledger
-> execution lane: native research-executor subagent | $team
-> evidence verification + Ultragoal checkpointing
-> terminal stories + installed Ultragoal final quality gate
-> evidence-backed ROADMAP.md / DECISIONS.md updates
```

## Supervisor / executor boundary

`reproduction-phase-loop` owns the phase lifecycle and should not be the default implementation owner.

The supervisor always owns:

1. evidence/spec inspection;
2. GPT-Pro gate management;
3. phase-plan / ralplan / ultragoal creation;
4. delegation to an execution lane;
5. result verification and Ultragoal checkpointing;
6. phase-exit GPT-Pro review;
7. evidence-backed `ROADMAP.md` / `DECISIONS.md` updates.

Execution is delegated by story shape:

- **Small/bounded story:** launch a native `research-executor` subagent with the Ultragoal story, phase plan, relevant spec/literature context, and required evidence-packet format.
- **Complex/parallel story:** use `$team` from the leader pane. Keep Ultragoal leader-owned; workers return task/evidence status only.

Direct implementation by the phase supervisor is reserved for trivial edits to lifecycle artifacts or emergency recovery where delegation would add risk. Even then, preserve the same evidence-packet and checkpoint discipline.

Phase success requires implementation/experiment evidence, phase-exit GPT-Pro review, completed terminal stories, and the installed Ultragoal final quality gate. A plan, phase-plan approval, or ralplan artifact is never phase success by itself.

## Canonical workflow

Run this loop for the selected phase until evidence-backed phase success:

```text
phase start
while phase is not evidence-complete:
  inspect local spec / current evidence
  identify latest literature / method gaps and stale assumptions
  run or reuse required/justified $gpt-pro-query
  verify, summarize, and challenge GPT-Pro output
  update docs/literature_survey/ only with curated primary-source-backed survey text

  run $phase-plan to draft/review notes/plans/phase-* directional plan
  if verdict is REVISE: revise the phase plan and re-review
  if verdict is ESCALATE_TO_RALPLAN: run $ralplan --deliberate

  create or update mandatory $ultragoal phase ledger from the approved phase plan or ralplan handoff
  verify goals.json contains core stories plus required preflight/terminal stories

  delegate the current executable story to native research-executor or $team with an execution packet
  verify the returned evidence packet
  if evidence is incomplete, weak, or unverifiable:
    do not checkpoint complete
    revise the execution packet and redispatch, or steer/split the story if the blocker changes scope
  else:
    checkpoint Ultragoal from concrete evidence
end while

complete terminal stories
satisfy the installed Ultragoal final quality gate
update ROADMAP.md and DECISIONS.md only from final evidence
```

## Non-negotiable invariants

### State and notes

- Do not mark `docs/reproduction_spec/ROADMAP.md` checkboxes as completed before concrete implementation, run, or verification evidence exists.
- Do not update `docs/reproduction_spec/DECISIONS.md` before phase evidence is sufficient for a finalized decision.
- Do not use component specs or `CANONICAL_SPEC.md` as work logs. Edit reproduction specs only when the user explicitly asks for spec revision.
- Stage pre-implementation phase plans under `notes/plans/phase-*/`, not in `ROADMAP.md` or `DECISIONS.md`.
- Store GPT-Pro artifacts under `notes/investigations/gpt_pro/<phase>/<date-topic>/` using `$gpt-pro-query`: thread metadata/anchor/synthesis plus per-turn prompt/response/integration files.
- Store curated, primary-source-checked survey updates under `docs/literature_survey/`; never paste GPT-Pro responses directly as survey text.

### Cluster and data operations

Before any MLXP, GPU, Docker, W&B, or D2E-data-dependent run, the supervisor must require an operational preflight story or evidence packet that confirms:

- `docs/reproduction_spec/OPERATIONAL_RULES.md` was read for current payload/path rules;
- local edit -> commit/push -> cluster clone pull -> run is the default path;
- the cluster clone path is `/mnt/ddn/prod-runs/jeonghunpark/code/continuous-gui-poc/fdm-1-with-d2e`;
- the D2E dataset path `/mnt/ddn/extra-ddn-continuous-gui/` is read-only;
- outputs, caches, checkpoints, pseudo-labels, reports, and temp files are never written inside the dataset tree;
- cluster jobs use a custom public Docker Hub image under `docker.io/pjh6029/fdm-1-with-d2e` with an immutable tag and recorded digest, not `latest` for training/evaluation;
- do not use the MLXP `debug` namespace/project for this repo; production reservations must stay within one node;
- non-trivial training/evaluation logs use W&B entity `pjh6029-seoul-national-university` and project `fdm-1-with-d2e`;
- idle GPU pods are cancelled, and reservations use the smallest efficient GPU count.

## Gate 1: GPT-Pro review

Invoke `$gpt-pro-query` at these gates unless a fresh, directly relevant artifact already exists and remains valid:

- Before VE finetuning: gameplay/screen-recording domain adaptation, SSL objective, encoder candidate.
- Before IDM implementation: masked diffusion / discrete diffusion / action inverse modeling objective.
- Before FDM implementation: diffusion vs AR vs hybrid, pseudo-label filtering, temporal conditioning.
- Before scaling/ablation: whether each axis has real research value.
- After a failed branch: what to abandon, modify, or test next.
- Before phase exit: whether evidence is sufficient to move to the next phase.

GPT-Pro roles include implementation critique, research/experiment critique, result review, phase pre-literature survey, and theoretical plausibility review. Do not let GPT-Pro decide alone; verify claims against primary sources and local evidence before using them.

## Gate 2: Phase plan and optional ralplan

Use `$phase-plan` for the phase-level research brief and quality control.

`notes/plans/phase-*` plan = **research/phase directional plan**:

- current spec/evidence summary;
- GPT-Pro/literature artifact links;
- agent interpretation, hypotheses, and uncertainty;
- high-level implementation direction;
- ablation/evaluation direction;
- cluster/resource plan;
- staged judgments that are not yet `ROADMAP.md` progress or `DECISIONS.md` decisions.

`$ralplan` artifact = **implementation-focused consensus handoff**:

- PRD/test-spec/ADR;
- concrete acceptance criteria;
- Architect -> Critic approval;
- execution-ready scope for `$ultragoal`, with `$team` candidates identified only as later execution lanes;
- durable `.omx/plans/` planning gate.

If `$phase-plan` escalates to `$ralplan`, keep the `notes/plans/phase-*` file as a thin index: why consensus planning is needed, what GPT-Pro/literature evidence to feed into it, and where the resulting `.omx/plans/` artifact lives. Do not duplicate PRD/test-spec detail in `notes/plans/`.

Before creating Ultragoal, `$phase-plan` must review the phase plan with sequential native subagents:

```text
phase plan draft
-> research-architect review
-> research-critic review
-> APPROVE | REVISE | ESCALATE_TO_RALPLAN
```

Review criteria:

- GPT-Pro/literature evidence is reflected in the plan;
- GPT-Pro claims are not trusted without primary-source or local-evidence verification;
- current spec conflicts are explicit;
- success/failure gates are measurable;
- ablation matrix is research-useful and operationally realistic;
- MLXP/GPU/data/W&B rules are respected;
- `ROADMAP.md` and `DECISIONS.md` are not used as pre-implementation logs;
- the plan is ready for Ultragoal or needs `$ralplan --deliberate`.

Verdicts:

- `APPROVE`: use the phase plan as the Ultragoal brief.
- `REVISE`: revise and re-review the phase plan.
- `ESCALATE_TO_RALPLAN`: run `$ralplan --deliberate` before Ultragoal.

## Gate 3: Mandatory Ultragoal phase ledger

Every ROADMAP phase must create or reuse an `$ultragoal` ledger. Do not run a plain ad-hoc execution path that bypasses Ultragoal.

Create goals from the approved phase plan or ralplan handoff, for example:

```sh
omx ultragoal create-goals --brief-file notes/plans/phase-<n>-<name>/YYYYMMDD-<topic>-plan.md
```

If ralplan was used, the Ultragoal brief must cite the `.omx/plans/` PRD/test-spec/ADR and the phase-plan index. Ultragoal remains leader-owned; `$team` is an execution lane for Ultragoal stories, not a replacement for the ledger.

Create the ledger in this order:

1. First derive core phase stories from the approved phase plan / ralplan:
   - implementation stories;
   - experiment / ablation stories;
   - evaluation stories;
   - cluster/run stories;
   - artifact/reporting stories.
2. Then append the mandatory terminal stories.

The terminal stories are append-only closure stories. They must not replace the core implementation, experiment, ablation, evaluation, or reporting stories derived from the approved phase plan or ralplan handoff.

Before accepting Ultragoal creation, inspect `.omx/ultragoal/goals.json` and verify it contains:

- at least one core implementation/experiment/evaluation story from the phase plan;
- an operational preflight story if any MLXP/data/GPU work is expected;
- a phase-exit GPT-Pro review story;
- an integration story;
- a `ROADMAP.md` update story;
- a `DECISIONS.md` update story;
- a notes/run-record completion story.

The ledger must include these story classes when applicable:

1. implementation stories;
2. experiment / ablation / evaluation stories;
3. operational preflight story before MLXP/GPU/D2E-data runs;
4. cluster/run and artifact/reporting stories;
5. mandatory terminal stories.

Mandatory terminal stories before phase exit:

1. **Run phase-exit GPT-Pro review** — submit current phase evidence as `result-phase-exit-review`, save prompt/response/integration, and produce a next-phase readiness verdict.
2. **Integrate phase-exit review** — verify/accept/reject recommendations against primary sources and local evidence; update `synthesis.md` and any curated literature notes if needed.
3. **Update `ROADMAP.md` from concrete evidence** — mark only checklist items backed by implementation, run, metric, checkpoint, report, or verification artifacts.
4. **Update `DECISIONS.md` from final supported decisions** — fill only finalized decision slots supported by phase evidence.
5. **Write/complete notes and run records** — ensure `notes/runs/`, `notes/experiments/`, `notes/investigations/`, or `notes/failures/` contain the necessary evidence pointers.

If any terminal story is missing, add it before phase exit with explicit Ultragoal steering, for example:

```sh
omx ultragoal steer \
  --kind add_subgoal \
  --title "Run phase-exit GPT-Pro review" \
  --objective "Submit current phase evidence as result-phase-exit-review, save prompt/response/integration artifacts, and return a next-phase readiness verdict." \
  --evidence "goals.json lacks a phase-exit review story" \
  --rationale "Phase exit is gated on GPT-Pro review and evidence integration."
```

Phase-exit review evidence must cite concrete artifacts such as:

```text
notes/investigations/gpt_pro/phase-X/.../turns/.../prompt.md
notes/investigations/gpt_pro/phase-X/.../turns/.../response.md
notes/investigations/gpt_pro/phase-X/.../turns/.../integration.md
notes/investigations/gpt_pro/phase-X/.../synthesis.md
```

Record story checkpoints with `omx ultragoal checkpoint --goal-id <id> --status complete --evidence "<artifact paths and verdict>" --codex-goal-json <fresh get_goal JSON or path>` when Codex goal reconciliation is required by Ultragoal.

Ultragoal final completion must also satisfy the installed Ultragoal final quality gate, including cleanup/review/verification and `--quality-gate-json` when required.

## Gate 4: Execution lane and evidence packet

- Use a native `research-executor` subagent for small or bounded Ultragoal stories. The assignment must include the execution packet below.
- Use `$team` from an Ultragoal story when independent lanes can run in parallel, e.g. implementation, tests/evaluation, cluster operations, and literature verification. The supervisor must launch, monitor, and shut down Team according to the `$team` lifecycle and checkpoint Ultragoal only from terminal Team evidence.
- Do not ask execution workers to mutate `.omx/ultragoal`, `ROADMAP.md`, or `DECISIONS.md`; workers return evidence packets and implications for the supervisor.
- Use native subagents for bounded in-session checks where durable tmux workers are unnecessary; use `$team` when durable tmux coordination, worktrees, or long-running parallelism is required.

Execution packet contract:

```markdown
- Ultragoal story id: `G003` from `.omx/ultragoal/goals.json`; include ledger status if retrying.
- Story objective: one bounded outcome, e.g. `Implement 50ms D2E action binning and round-trip tests`.
- Phase plan path: e.g. `notes/plans/phase-0-data/20260605-data-foundation-plan.md`.
- Ralplan artifact path, if any: e.g. `.omx/plans/prd-data-foundation.md`, `.omx/plans/test-spec-data-foundation.md`; otherwise `none`.
- GPT-Pro thread/integration paths: e.g. `notes/investigations/gpt_pro/phase-0-data/20260605-action-tokenization/turns/001-.../integration.md` and `synthesis.md`; otherwise `none`.
- Relevant spec paths: e.g. `docs/reproduction_spec/CANONICAL_SPEC.md`, `docs/reproduction_spec/spec/data_and_actions.md`, `docs/reproduction_spec/spec/evaluation.md`.
- Relevant code/config/test paths: e.g. `src/fdm_1_with_d2e/data/`, `configs/data/`, `tests/unit/data/`; include expected new paths if files do not exist yet.
- Operational constraints: e.g. `local-only tests for this story`, or `MLXP preflight required; dataset read-only; commit/push before cluster pull; W&B entity/project required`.
- Expected evidence packet: required verification and artifact shape, e.g. `changed files, pytest command/output, generated manifest fixture path, known risks, recommended Ultragoal checkpoint`.
```

If an execution lane returns incomplete, weak, or unverifiable evidence, do not checkpoint the story as complete. Revise the execution packet and redispatch the same story, or steer/split the story if the blocker changes scope.

## Progress evidence and closure

Before claiming phase progress, gather concrete evidence appropriate to the phase:

- local tests/lint/typecheck/build for code changes;
- MLXP run record with git SHA, image tag/digest, config, dataset/split manifest, W&B link when applicable;
- metrics/checkpoint/report artifact pointers outside the dataset tree;
- GPT-Pro phase-exit review artifact;
- phase plan, ralplan handoff when used, Ultragoal ledger checkpoints, and integration notes under `notes/`.

Only after that evidence exists, update `ROADMAP.md` checkboxes/status. Only after final phase conclusions exist, update `DECISIONS.md` slots.

## Anti-patterns

- Do not treat the canonical spec as frozen when phase evidence contradicts it; stage revised plans first and ask for spec edits only when needed.
- Do not let GPT-Pro decide alone. The agent must verify claims against primary sources and local evidence.
- Do not run `$team` without a leader-owned Ultragoal ledger.
- Do not let the phase supervisor become the default implementation owner; delegate executable stories unless the task is trivial lifecycle maintenance.
- Do not let workers update Ultragoal, ROADMAP, or DECISIONS directly; they provide evidence packets for supervisor-owned checkpoint/update.
- Do not mark phase success because a plan, phase-plan approval, or ralplan artifact exists. Success requires implementation/experiment evidence and phase-exit review.
- Do not create an Ultragoal phase ledger without the mandatory terminal stories.
