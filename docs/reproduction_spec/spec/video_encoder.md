# Video Encoder

## Role

Compress D2E video frames from all games into a shared visual token space suitable for IDM and FDM.

The encoder should handle:

- 3D scenes
- 2D scenes
- menus
- UI overlays
- text-heavy screens
- cursor/crosshair movement
- rapid camera motion
- low-motion or idle segments

## Input

```
D2E video frames
sampled at 20fps or grouped from 60fps into 50ms bins
```

## Output

```
compressed video tokens per 50ms bin
```

## Video Encoder backbone

Use pretrained V-JEPA 2 as the PoC video encoder backbone.

The main PoC should not train a custom video encoder from scratch.
Instead, it should evaluate whether V-JEPA 2 can be adapted into a useful FDM-1-style compressed video representation for D2E.

### VE-0: Frozen V-JEPA 2 + linear/shallow probes

Purpose:

- establish whether pretrained V-JEPA 2 features already contain useful information for D2E action prediction.

Training:

- freeze V-JEPA 2
- train only shallow probes for:
    - mouse movement
    - keyboard events
    - mouse buttons
    - next-action prediction

Evaluation:

- frozen feature action probe
- per-game and per-category metrics

Use for:
- diagnosing whether V-JEPA 2 features preserve gameplay-relevant information

### VE-1: Frozen V-JEPA 2 + trainable temporal compressor

Recommended first main candidate.

Architecture:

```
D2E frames
  → frozen V-JEPA 2
  → trainable temporal compressor / Perceiver resampler
  → fixed number of video tokens per 50ms bin
```

Training:

- freeze V-JEPA 2
- train resampler/compressor
- train IDM/FDM on compressed tokens

Token budget:

- 4 video tokens / 50ms bin default
- ablate 8 and 16 tokens / bin

Pros:

- stable
- efficient
- avoids destroying pretrained representation
- suitable for H200 x4 first-pass experiments

Use for:

- main IDM/FDM runs
- most ablations
- pseudo-label usefulness study

### VE-2: V-JEPA 2 last-block / adapter / LoRA finetuning

Architecture:

```
D2E frames
  → V-JEPA 2 with LoRA/adapters or last-N-block finetuning
  → temporal compressor / resampler
  → compressed video tokens
```

Training:

- freeze lower V-JEPA 2 blocks
- finetune only:
    - LoRA/adapters
    - last N blocks
    - temporal compressor

Purpose:

- adapt V-JEPA 2 to D2E-specific visual features:
    - HUD
    - crosshair
    - cursor
    - UI text
    - menus
    - fast camera motion
    - small objects

Use for:

- testing whether D2E domain adaptation improves IDM/FDM
- comparing against VE-1

### VE-3: V-JEPA 2 domain adaptation with masked video objective

Architecture:

```
D2E video
  → V-JEPA 2 backbone
  → masked latent prediction / JEPA-style adaptation
  → temporal compressor
```

Training objective:

```
mask temporal spans and/or spatial regions
predict teacher latent features of masked frames
```

Recommended:

- use action labels only for probes or downstream training, not as the primary video encoder objective.
- primary objective should remain self-supervised video representation adaptation.

Purpose:

- test whether self-supervised D2E video adaptation improves downstream action modeling.

Use for:

- RQ5 scale trend
- video encoder ablation

### VE-4: End-to-end finetuned V-JEPA 2 with IDM/FDM

Optional, not default.

Architecture:

- V-JEPA 2 + temporal compressor + IDM/FDM are trained jointly.

Purpose:

- test upper-bound downstream performance.

Risks:

- expensive
- harder to attribute improvements
- may overfit to D2E actions
- may reduce interpretability of video encoder stage

Use only after VE-1 / VE-2 are stable.

## Video Encoder training objective

For VE-1:

- train compressor through downstream IDM/FDM losses.
- optionally add masked latent prediction loss.

For VE-2 / VE-3:

- use a combination of:
    - masked latent prediction
    - downstream IDM loss
    - downstream FDM loss, if doing joint finetune
    - optional reconstruction or contrastive regularization

Default recommendation:

```
L_VE =
  L_masked_latent_prediction
```

for domain adaptation, followed by downstream IDM/FDM training.

For joint finetuning:

```
L_total =
  L_downstream
  + λ_ve * L_masked_latent_prediction
```

## Video Encoder evaluation

Primary:

1. frozen V-JEPA 2 action probe
2. V-JEPA 2 + compressor IDM downstream performance
3. V-JEPA 2 + compressor FDM downstream performance
4. VE candidate comparison:
    - VE-0
    - VE-1
    - VE-2
    - VE-3
    - optional VE-4
5. compression / throughput
6. per-game and macro-game performance

Baselines:

- no-op / zero-mouse baseline
- previous-action repeat baseline
- action-history-only baseline
- frozen image encoder + shallow probe, optional
- raw-frame baseline, optional if compute allows

Success criteria:

- V-JEPA 2 features improve action prediction beyond action-only and no-op baselines.
- VE-1 or VE-2 improves IDM/FDM downstream performance over VE-0.
- gains appear across multiple game categories, not only FPS or one high-resource game.
- higher token budget or adaptation shows measurable improvement, unless the task is bottlenecked by labels/action ambiguity.