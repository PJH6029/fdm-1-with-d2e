# Video Encoder

Canonical source: `../CANONICAL_SPEC.md`; survey context: `../../literature_survey/VIDEO_ENCODER.md`.

## Role

Learn a compact D2E gameplay/screen-recording representation for IDM and FDM. The encoder must preserve control-relevant visual state across 2D games, 3D/FPS games, open-world/sandbox games, menus, HUDs, UI overlays, tiny text/icons, cursor/crosshair movement, rapid camera motion, and low-motion segments.

Core assumption: generic pretrained video encoders are useful initializations, but they should not be assumed to contain enough computer/gameplay domain knowledge. D2E gameplay-domain adaptation is a central reproduction task, not a minor token-selection detail.

## Input/output

```text
D2E 60fps gameplay/screen video aligned to 50ms bins
  → compact video tokens/features per 50ms bin
  → IDM/FDM
```

The output must be cacheable and reproducible from a dataset manifest, git SHA, encoder checkpoint/config, adaptation config, and feature-cache format.

## Candidate and adaptation set

### VE-0 — frozen pretrained encoder bakeoff

Purpose: measure the domain gap before expensive adaptation.

Candidates, subject to engineering availability:

- V-JEPA 2 / 2.1 as the FDM-1-adjacent JEPA-style initialization;
- VideoPrism as a strong general frozen video encoder challenger;
- VideoMAE v2 or InternVideo2-style candidates if practical.

Run identical D2E action/screen probes and Tiny-IDM/Tiny-FDM transfer. VE-0 is diagnostic and should not be treated as sufficient unless it unexpectedly performs well on held-out games and long-context compression.

### VE-1 — frozen encoder + trainable temporal resampler

Purpose: test whether learned temporal token selection/compression over frozen features is enough.

```text
frames/window → frozen pretrained encoder → temporal resampler/Perceiver → fixed video tokens per 50ms bin
```

Use as the frozen reference for token budget and cache economics. If VE-1 fails on HUD/UI/cursor/crosshair or held-out-game action metrics, the remedy is encoder adaptation, not only a larger resampler.

### VE-2 — D2E gameplay adapter / LoRA / last-block adaptation

Main practical adaptation candidate.

Purpose: inject D2E gameplay/screen domain knowledge while preserving pretrained features and keeping compute feasible.

Adapt:

- LoRA/adapters;
- last N blocks;
- temporal resampler;
- optional lightweight screen-state heads.

Targets:

- action-probe utility;
- HUD/UI/cursor/crosshair sensitivity;
- held-out-game generalization;
- downstream Tiny-IDM/Tiny-FDM improvements.

### VE-3 — D2E self-supervised gameplay video adaptation

Main representation-learning candidate.

Train on D2E video with masked latent/video prediction before downstream IDM/FDM training. Labels are used for probes and downstream validation, not as the primary self-supervised target.

Recommended objectives:

- masked latent prediction using a teacher/frozen target;
- temporal span prediction for long-context state;
- optional spatial masking biased toward UI/HUD/cursor/text regions if diagnostics justify it.

### VE-4 — screen/game auxiliary adaptation

Use when diagnostics show specific screen-domain failures.

Possible auxiliary targets/probes:

- cursor/crosshair localization;
- HUD/text/menu region sensitivity;
- next-click or click-target location;
- low-motion state-change detection;
- active-window/game-state metadata where appropriate.

These auxiliaries are not the main final metric; they are tools to fix representation failures that hurt IDM/FDM.

### VE-5 — end-to-end finetuning with IDM/FDM

Optional upper-bound only. Use after VE-2/VE-3 are stable because it is expensive, harder to attribute, and can overfit action labels.

## Evaluation and promotion

Evaluate the video encoder as a first-class research stage.

### Eval VE-A — domain-gap probes

Freeze each encoder candidate and train identical probes on cached features.

Probe targets:

- 50ms-bin mouse movement;
- keyboard event presence/key family;
- mouse button event presence;
- cursor/crosshair or next-click position where feasible;
- UI/HUD/text/menu-sensitive probes when labels or heuristics are available.

Report micro-average, per-game macro-average, and held-out-game macro-average.

### Eval VE-B — downstream transfer

Train fixed-budget Tiny IDM/FDM heads with the same data, action tokenization, model budget, and schedule for every VE candidate.

Report:

- Tiny-IDM D2E primary metrics;
- Tiny-FDM teacher-forced metrics;
- logged free-running stability for the best VE candidates;
- whether gains persist on held-out games.

### Eval VE-C — long-context compression

Measure whether the representation supports long video context without losing action-relevant state.

Report:

- tokens per 50ms bin;
- cache size per video-hour;
- maximum practical context length;
- performance degradation from short to longer contexts;
- state-retention failures in menus, inventory, navigation, and low-motion segments.

### Eval VE-D — adaptation safety

For VE-2/VE-3/VE-5, compare pre-adaptation and post-adaptation behavior.

Reject or demote an adapted encoder if:

- improvements appear only on train/in-distribution games;
- held-out-game action metrics regress;
- feature norms/token entropy suggest collapse;
- downstream IDM/FDM becomes less stable;
- cache/training cost makes 50%/100% scale runs infeasible.

### Eval VE-E — operational efficiency

Report:

- feature extraction FPS or video-hours/GPU-hour;
- cache size per video-hour;
- GPU memory and batch size;
- downstream training throughput;
- inference latency.

## Promotion rule

- Frozen encoders and VE-1 are references for domain-gap measurement and token-budget economics.
- VE-2 or VE-3 should be attempted unless frozen features unexpectedly meet held-out/downstream requirements.
- Promote an adapted VE only if it improves held-out/downstream action metrics or fixes a documented screen/game perception failure without breaking scale feasibility.
- Promote at most 1–2 VE settings to Base IDM/FDM runs.
