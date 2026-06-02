# Evaluation

## Online rollout policy

Online rollout is out of scope for this PoC.

Reason:

- D2E is a logged dataset, not an interactive environment.
- The planned hardware target is an H200 GPU training cluster, not a game/VM rollout cluster.
- True online control would require reproducible game environments, reset logic, game state instrumentation, and latency-sensitive inference infra.
- This PoC is about validating FDM-1-style video-action pretraining under D2E, not demonstrating game-solving behavior.

Therefore, Phase 1 evaluation must be entirely offline.

No online rollout metric is required for success.

## Evaluation modes

### Eval A: Offline IDM action reconstruction

Purpose:

- answer whether IDM can pseudo-label D2E gameplay.

Input:

- video tokens
- masked action slots

Compare:

- IDM predicted actions vs GT D2E actions

Metrics:

- mouse movement Pearson correlation X/Y
- mouse movement scale ratio X/Y
- mouse button accuracy / F1
- keyboard per-key accuracy / F1
- masked action NLL
- top-k action accuracy
- calibration
- per-game macro-average
- held-out-game metrics

Primary RQs:

- RQ1
- RQ2

### Eval B: Pseudo-label usefulness

Purpose:

- answer whether IDM pseudo-labels are good enough to train FDM.

Train:

- FDM-GT on GT labels
- FDM-Pseudo on IDM pseudo-labels
- FDM-FilteredPseudo on confidence-filtered pseudo-labels
- FDM-Mix on GT + pseudo-labels

Evaluate:

- same GT-labeled held-out test set

Main metrics:

- FDM-Pseudo / FDM-GT performance ratio
- FDM-FilteredPseudo improvement over FDM-Pseudo
- FDM-Mix gap to FDM-GT

Primary RQ:

- RQ3

Example reporting:

```
FDM-GT mouse Pearson: 0.60
FDM-Pseudo mouse Pearson: 0.48
Pseudo/GT ratio: 80%
```

### Eval C: Offline teacher-forced FDM evaluation

Purpose:

- evaluate next-action prediction under logged human trajectories.

Input:

- logged video
- GT or pseudo previous actions, depending on model

Metrics:

- next-action NLL
- top-1 / top-k action accuracy
- mouse movement Pearson correlation X/Y
- mouse movement scale ratio X/Y
- mouse dequantized L1/L2 error
- keyboard per-key accuracy
- keyboard precision / recall / F1
- mouse button accuracy / F1
- click-position error
- no-op false positive rate
- no-op false negative rate
- action event edit distance
- long-context degradation curve

Report by:

- all clips micro-average
- game macro-average
- per-game
- per-category
- high-mouse-motion segments
- high-keyboard-activity segments
- menu/UI-heavy segments
- low-motion / idle segments
- held-out games

Primary RQs:

- RQ1
- RQ4
- RQ5

### Eval D: Free-running-on-logged-video

This is not online rollout.

Logged video remains fixed, but model-generated actions are fed back into the action-history input.

Procedure:

```
for each held-out clip:
  condition on first N seconds of GT actions
  then repeatedly:
    input logged video frames
    input model’s own previous predicted actions
    predict next action
```

This does not test true closed-loop environment control, because video does not respond to the model’s actions.

But it tests:

- action-history compounding
- key-state drift
- no-op collapse
- mouse trajectory drift relative to logged human actions
- stability across different game types

Metrics:

- same action metrics as offline teacher-forced evaluation
- degradation over rollout horizon
- key/button state consistency
- mouse drift over time

Primary RQs:

- RQ4
- RQ5

### Eval E: Scale trend evaluation

Purpose:

- answer whether the FDM-1-style recipe scales on D2E.

Train on:

```
1%
5%
10%
25%
50%
100%
```

Evaluate:

- IDM quality vs data scale
- FDM-GT vs data scale
- FDM-Pseudo vs data scale
- Pseudo/GT ratio vs data scale
- held-out-game performance vs data scale
- context length sensitivity vs data scale

Primary RQ:

- RQ5