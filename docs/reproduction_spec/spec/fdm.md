# FDM

## Role

Train a forward dynamics model that predicts the next action given prior video and prior actions across all D2E games.

## Input

```
past compressed video tokens
+ past action tokens
```

Optional:

- game ID embedding
- active window embedding
- current key/button state tokens

Default PoC:

- do not use audio
- do not use game ID in the main generalization experiment
- allow game ID only as an ablation

Reason:

- game ID can improve in-distribution score but may obscure whether a shared cross-game policy/action model is being learned.

## Output

Main:

- next 50ms bin action sequence

Optional:

- next-click-position auxiliary target
- key/button state auxiliary target
- action chunk over next H bins

## Architecture

Recommended PoC architecture:

```
video tokens
+ action tokens
+ modality embeddings
+ temporal position embeddings
→ causal transformer
→ next-action heads
```

Model sizes:

Tiny FDM:

```
d_model: 512
layers: 8
heads: 8
context: 10s to 30s
```

Base FDM:

```
d_model: 768
layers: 12
heads: 12
context: 30s to 120s
```

Use Tiny for broad ablations.
Use Base only for final selected configurations.

## Context length

Initial:

```
10s context = 200 action bins at 50ms
```

Ablations:

```
2s
5s
10s
30s
60s
```

Purpose:

- measure whether longer video/action context improves action prediction across different game types.

## FDM candidates

### FDM-0: No-op / zero-mouse baseline

Purpose:

- establish lower bound.

### FDM-1: Previous-action repeat baseline

Purpose:

- test action inertia baseline.

### FDM-2: ActionOnly transformer

Input:

- past action tokens only

Purpose:

- measure how much performance comes from action autocorrelation.

### FDM-3: VideoOnly transformer

Input:

- past video tokens only

Purpose:

- measure whether visual state alone is predictive.

### FDM-4: FDM-GT

Input:

- past video tokens + past GT actions

Train labels:

- GT actions

Purpose:

- oracle upper bound at D2E scale.

### FDM-5: FDM-Pseudo

Input:

- past video tokens + past IDM-pseudo actions

Train labels:

- IDM pseudo-labels

Purpose:

- FDM-1-style reproduction.

### FDM-6: FDM-FilteredPseudo

Input:

- video + confidence-filtered pseudo-actions

Purpose:

- test whether pseudo-label filtering improves downstream FDM.

### FDM-7: FDM-Mix

Input:

- video + action tokens

Train labels:

- mixture of GT and pseudo-labels

Purpose:

- test whether limited GT data stabilizes pseudo-label training.

### FDM-8: FDM-GT with game ID, ablation only

Input:

- video tokens
- action tokens
- game ID embedding

Purpose:

- estimate upper bound with game conditioning.

Caution:

- not the main result, because game ID can obscure generalist cross-game learning.

### FDM-9: FDM-Pseudo with game ID, ablation only

Purpose:

- test whether game conditioning helps pseudo-label-trained FDM.

## FDM training objective

Teacher-forced autoregressive next-action prediction.

If using fixed K slots:

```
L_FDM =
  CE(mouse movement token)
  + mean_k CE(event slot k)
  + λ_click * CE(next click position)
  + λ_state * BCE(next key/button state)
```

Class imbalance:

- no-op and zero movement dominate.
- use class-balanced reporting.
- optionally use loss weighting or balanced sampling.

Recommended:

- report both weighted and unweighted metrics.
- avoid aggressive rare-event weighting early, because it may increase false-positive actions.