# IDM

## Role

Train an inverse dynamics model on labeled D2E recordings and use it to pseudo-label action labels from video-only gameplay.

## Input

```
compressed video tokens from a non-causal observation window
+ masked action tokens for target bins
```

Recommended observation design:

```
target action bin: [t, t+50ms)

condition on video frames around the target:
  past context: t - C_past to t
  future context: t to t + C_future
```

Use future context because inverse dynamics is non-causal.

Recommended future offset:

- τ = 100ms default
- ablate 0ms, 50ms, 100ms, 150ms, 200ms

## Sequence format

```
VideoBin_{t-N}
ActionSlots_{t-N}
...
VideoBin_t
MASK_ACTION x slots
VideoBin_{t+1}
MASK_ACTION x slots
...
VideoBin_{t+M}
```

The IDM can attend bidirectionally to all video tokens and all action/mask tokens.

## Architecture

Recommended PoC architecture:

```
video token embeddings
+ action token embeddings
+ temporal position embeddings
+ modality embeddings
→ bidirectional transformer
→ action-token classification heads for masked positions
```

Model sizes:

Tiny:

```
d_model: 512
layers: 8
heads: 8
context: 10s to 30s
```

Base:

```
d_model: 768
layers: 12
heads: 12
context: 30s to 120s
```

Start with Tiny for broad ablations, then promote the best candidates to Base.

## IDM candidates

### IDM-0: Majority / no-op baseline

Purpose:

- baseline for sparse event dominance.

Prediction:

- zero mouse movement or previous distribution
- no keyboard/mouse-button events

### IDM-1: Action-prior baseline

Purpose:

- measure how much can be predicted from game/action statistics without visual information.

Input:

- game-agnostic or per-game action prior
- optional previous action context
- no video

### IDM-2: Causal IDM

Purpose:

- baseline against non-causal inverse dynamics.

Input:

- past video only
- no future video context

### IDM-3: Non-causal IDM

Main IDM candidate.

Input:

- past + future video context
- masked action slots

Ablations:

- future offset τ = 0ms, 50ms, 100ms, 150ms, 200ms
- context length = 1s, 5s, 10s, 30s
- K action slots = 4, 8, 16
- compound mouse token vs separate dx/dy tokens
- VE candidate = VE-1 vs VE-2 vs VE-3

### IDM-4: Non-causal IDM + confidence calibration

Purpose:

- improve pseudo-label quality for FDM training.

Methods:

- temperature scaling
- confidence thresholding
- entropy filtering
- per-token-type thresholding
- sparse event filtering

Used for:

- generating D_PSEUDO_FILTERED

### IDM-5: Per-game specialist IDM, optional

Purpose:

- upper-bound per-game labelability.
- compare generalist model vs specialist models.

Use:

- only if compute allows.
- not the main reproduction target.

## IDM training objective

Masked denoising / masked diffusion over action slots.

Simplified PoC objective:

```
randomly mask action slots
predict original action tokens
cross-entropy over masked positions
```

FDM-1-style iterative inference:

```
1. initialize target action slots as MASK_ACTION
2. predict log probabilities for all masked positions
3. unmask top-k highest-confidence predictions
4. repeat for S steps
```

Recommended:

- S = 8 or 16 steps
- mask ratio sampled from 0.1 to 1.0
- include fully masked target windows

Loss:

```
L_IDM =
  CE(action token)
  + λ_click * CE(next-click-position optional)
  + λ_state * BCE(key/button state optional)
```

## IDM evaluation

Use D2E-style 50ms-bin metrics as primary.

Primary:

- mouse movement Pearson correlation X/Y
- mouse movement scale ratio X/Y
- mouse button accuracy
- keyboard per-key accuracy

Additional:

- masked action NLL
- top-1 / top-k action accuracy
- per-action-type accuracy
- mouse dequantized L1/L2 error
- key event precision / recall / F1
- mouse button precision / recall / F1
- event edit distance per second
- calibration: confidence vs correctness, ECE
- overflow rate for fixed K slots

Report all metrics:

- micro-average over all data
- macro-average over games
- per-game
- per-category
- in-distribution
- held-out-game

Important comparisons:

```
IDM-NonCausal vs IDM-Causal
IDM-NonCausal vs IDM-ActionPrior
IDM with VE-1 vs VE-2 vs VE-3
IDM with different τ
IDM generalist vs per-game specialist, optional
```

Success criteria:

- IDM-NonCausal should outperform IDM-Causal.
- IDM should outperform no-op and previous-action baselines across most games.
- IDM should produce useful pseudo-labels for multiple game categories.
- Sparse keyboard/button metrics must be reported separately from mouse metrics.

# Pseudo-labeling Pipeline

## Purpose

Mimic FDM-1’s pseudo-labeling stage within D2E.

Procedure:

```
1. Train IDM candidates on labeled subset.
2. Select best IDM variants by validation metrics.
3. Hide labels for pseudo-label subset.
4. Run IDM inference over pseudo-label subset.
5. Write predicted actions as MCAP or packed action-token dataset.
6. Train FDM candidates on pseudo-labeled subset.
```

## Confidence filtering

For each predicted token:

- store probability
- store entropy
- store token type
- store game ID
- store timestamp

Filtering options:

- keep all pseudo-labels
- drop low-confidence sparse events
- replace low-confidence sparse event slots with NO_ACTION
- downweight low-confidence labels in FDM loss
- use per-token-type confidence thresholds

Recommended initial policy:

- keep all mouse movement predictions
- filter only sparse keyboard/mouse-button events below threshold
- tune threshold on validation set, not per test game

Create datasets:

```
D_GT:
  GT action labels

D_PSEUDO_ALL:
  all IDM predictions

D_PSEUDO_FILTERED:
  confidence-filtered IDM predictions

D_MIX:
  GT + pseudo-labels
```