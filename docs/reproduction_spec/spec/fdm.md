# FDM

Canonical source: `../CANONICAL_SPEC.md`.

## Role

Train a forward dynamics/action model that predicts the next 50ms action bin from causal video tokens and previous actions. The ultimate goal is to match the closed-source FDM-1 FDM behavior/performance envelope. This local model is evaluated offline, in logged free-running mode, and in a desktop/game or replay-control harness.

## Input/output

For target action bin `A_t = [t, t+50ms)`:

```text
causal compressed video tokens available at decision time t
+ previous action tokens A_<t
→ action tokens for A_t
```

Hard rule: **FDM must not use future visual evidence.** No frame or video token whose timestamp is after decision time `t` may condition prediction of `A_t`.

`VideoBin_t` is allowed only if the implementation defines it as an observation ending at or before `t`. If `VideoBin_t` is computed from frames inside `[t, t+50ms)`, it leaks target-interval visual evidence and must not be used to predict `A_t`; use `VideoBin_<t` or re-index the visual bin instead.

Optional inputs/heads:

- current key/button state tokens if derived causally from `A_<t`;
- next-click-position auxiliary head;
- game ID embedding as an ablation only;
- action chunk prediction only after single-bin prediction is stable.

## Prediction unit and architecture ablations

The 50ms action bin is represented by one mouse-move token or axis-token pair plus `K` event slots. Because every slot is a token-level decision, the FDM prediction unit is an explicit architecture ablation rather than a single fixed assumption.

### FDM-SerializedAR

Predict the target bin as an intra-bin autoregressive token stream:

```text
video/action causal context
→ MOUSE_MOVE_t
→ EVENT_SLOT_1_t
→ ...
→ EVENT_SLOT_K_t
```

Use teacher forcing during training. This preserves token dependencies and event ordering, but it is slower and more exposed to intra-bin rollout errors.

### FDM-MultiHead

Predict all target-bin slots from the same causal hidden state with independent heads:

```text
causal hidden state at t
  ├── mouse movement head or dx/dy heads
  ├── event-slot-1 head
  ├── ...
  └── event-slot-K head
```

This is faster and simple to evaluate, but it may under-model dependencies between mouse movement and sparse events. Treat serialized-token vs independent-head prediction as a required FDM ablation.

Default order:

1. implement Tiny versions of both `FDM-SerializedAR` and `FDM-MultiHead`;
2. compare held-out token metrics, sparse-event behavior, and logged free-running stability;
3. promote only the better recipe to Base-scale runs unless the results are complementary.

## Action token factorization

FDM must consume the tokenization variants defined in `data_and_actions.md`; it should not hard-code one action vocabulary as the only valid reproduction path.

Required compatibility:

- compound mouse token: `MOUSE_MOVE_BIN_<xbin>_<ybin>`;
- optional separate-axis tokens/heads: `MOUSE_DX_BIN_<i>`, `MOUSE_DY_BIN_<j>`;
- fixed event slots `EVENT_SLOT_1..K` with `NO_ACTION`, `PAD_ACTION`, and `EVENT_OVERFLOW` semantics;
- optional click-position auxiliary target.

Action-factorization ablations are tied to the prediction-unit ablation:

- serialized token stream vs independent multi-head prediction;
- compound mouse token vs separate dx/dy factorization;
- shared event-slot vocabulary vs slot-specific event heads if slot imbalance becomes severe.

## Candidate and target set

Local candidates intentionally avoid the name `FDM-1` to prevent confusion with the public FDM-1 model.

### FDM-1 FDM target

The closed-source FDM-1 FDM is the ultimate reproduction target. There is no public FDM checkpoint or exact harness, so this target is evaluated through a documented gap analysis:

- alignment with public FDM-1 recipe and action-token semantics;
- D2E held-out action prediction quality;
- logged free-running stability;
- desktop/game or replay-control harness behavior;
- explicit limitations from smaller D2E data volume, missing private transcripts/language grounding, and closed-source architecture gaps.

### Floor baselines and diagnostics

- **FDM-B0:** no-op / zero-mouse floor.
- **FDM-B1:** previous-action repeat floor.
- **FDM-B2:** action-only transformer diagnostic.
- **FDM-B3:** video-only transformer diagnostic.

These are required checks, but beating them is not the final FDM reproduction target.

### Main candidates

- **FDM-GT:** video + past GT actions, trained on GT labels.
- **FDM-Pseudo:** trained on unfiltered IDM pseudo-labels.
- **FDM-FilteredPseudo:** trained on calibrated/confidence-filtered pseudo-labels.
- **FDM-Mix:** trained on GT + pseudo-label mixture.
- **FDM-GeneralistIDM-Pseudo:** optional comparison trained on D2E-Generalist-IDM-1B pseudo-labels, only if inference/output compatibility is practical.
- **FDM-GameID:** optional ablation only, because game ID can mask weak cross-game generalization.

## Training objective

Teacher-forced next-action prediction under the selected prediction-unit recipe.

For multi-head fixed action slots:

```text
L_FDM = CE(mouse movement token or dx/dy tokens)
      + mean_k CE(event slot k)
      + λ_click * CE(next-click position, optional)
      + λ_state * state loss(optional)
```

For serialized intra-bin autoregression:

```text
L_FDM = sum_{slot in [mouse, event_1, ..., event_K]} CE(next slot token | causal context, previous target-bin slots)
      + optional auxiliary losses
```

Class imbalance handling:

- no-op and zero mouse movement dominate; report metrics by token family;
- use balanced sampling/loss weighting cautiously and track false-positive sparse events;
- always report unweighted headline metrics plus any weighted training loss.

## Pseudo-label training recipe

Pseudo-label training is a required research axis, not a single fixed preprocessing step.

Pseudo-label sources:

- our promoted masked-diffusion IDM;
- D2E-Generalist-IDM-1B only as an optional comparison if its inference path and output schema are compatible.

Filtering ablations:

- no filtering: train on all pseudo labels;
- per-token confidence filtering or loss weighting;
- per-bin confidence filtering or loss weighting;
- threshold/coverage sweeps for each filtering policy.

Low-confidence handling ablations:

- drop low-confidence tokens/bins from the loss;
- keep low-confidence labels with reduced loss weight;
- replace low-confidence event slots with `PAD_ACTION`/ignored loss while keeping causal context when safe;
- keep bins for video/action context but mask their supervised loss.

GT/pseudo mixture ablations:

- GT-only upper reference under D2E labels;
- pseudo-only;
- filtered-pseudo-only;
- GT:pseudo mixture-ratio sweep, initially `1:0`, `1:1`, `1:4`, `1:16`, and `0:1` if data volume allows;
- curriculum option: start GT-heavy, then anneal toward pseudo-heavy only if validation improves.

Required reporting:

- coverage retained by filtering policy;
- pseudo-label no-op/event-rate drift versus GT;
- FDM-Pseudo/FDM-FilteredPseudo/FDM-Mix performance relative to FDM-GT;
- whether filtering improves metrics at matched coverage or only hides hard examples.

## Context lengths

Start small and scale only when throughput is proven:

- short: `2s`;
- default medium: `10s`;
- longer: `30s+` only after 10s context wins and training/inference remains efficient.

## Evaluation

Primary evidence:

1. FDM-1 target-gap analysis from public claims, recipe alignment, harness behavior, and known limitations;
2. teacher-forced NLL/cross-entropy by token family;
3. D2E-style action metrics after converting predictions to event outputs;
4. sparse keyboard/button precision/recall/F1;
5. no-op false-positive/false-negative rates;
6. logged free-running degradation and state consistency;
7. harness stability for the selected checkpoint.

Success requires an explicit FDM-1 target-gap report. Beating simple floor baselines on per-game macro-average is mandatory evidence, but it is not sufficient to claim FDM-1-level reproduction.

## Open risks and future-work items

These items are important for the serious reproduction claim, but should be specified after the first Tiny/Base FDM measurements expose the dominant failure modes.

### Teacher-forcing vs free-running mismatch

Pure teacher forcing may overstate FDM quality because harness execution feeds back model-predicted previous actions. If logged free-running degrades sharply, add controlled ablations such as action-context dropout, predicted-action context corruption, scheduled sampling, or short rollout training. Report these as exposure-bias mitigation rather than replacing the primary teacher-forced metric.

### FDM-1 target-gap rubric

The target-gap rubric should become more operational once local harness categories are fixed. It should separate direct evidence, proxy evidence, and known gaps, and it must forbid claiming exact FDM-1 parity without direct comparable evidence or public checkpoint access.

### Video encoder/FDM binding

FDM quality depends on the video representation. Candidate bindings should include frozen pretrained/adapted VE, lightweight adapter/LoRA-style VE adaptation, and full VE finetuning only if compute permits. Keep the FDM recipe comparable when testing VE changes.

### Model scale definition

Tiny/Base currently indicate experiment role, not a fixed architecture. Later specs should define parameter ranges, context-token budgets, batch/compute targets, and promotion rules so Base runs are not wasted on full factorial sweeps.

### Harness inference and safety policy

Harness execution needs a fixed inference policy: greedy vs sampling, temperature/top-k settings, invalid-action repair, stuck-key/button release guards, and mouse-delta clipping. Safety repair should be reported separately from raw model quality.

### Transcript/language grounding gap

Public FDM-1 uses transcripts/language grounding, but the D2E-first reproduction does not initially model transcript tokens. Treat this as a documented limitation and optional future extension, not as part of the initial D2E FDM success claim.
