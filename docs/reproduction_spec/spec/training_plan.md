# Training Plan

## Phase 0: Data pipeline and baselines

Deliverables:

- D2E / OWAMcap reader
- video frame sampler
- 50ms action binning
- action tokenizer
- action de-tokenizer
- MCAP writer for predicted actions
- evaluation wrapper around D2E-style metrics
- per-game and per-category split manifest
- data scale split manifest

Checks:

- video timestamps align with input events
- keyboard/mouse overlays match visualizer
- raw HID deltas reconstruct plausible mouse movement
- no-op distribution is logged
- event overflow rate is logged
- per-game hours and action distributions are logged

Baselines:

- no-op baseline
- zero-mouse baseline
- previous-action repeat baseline
- action-only transformer
- V-JEPA 2 frozen action probes

## Phase 1: Video Encoder ablations

Candidates:

- VE-0: frozen V-JEPA 2 + probes
- VE-1: frozen V-JEPA 2 + trainable temporal compressor
- VE-2: V-JEPA 2 LoRA/adapters or last-block finetuning
- VE-3: V-JEPA 2 masked video domain adaptation
- VE-4: end-to-end finetuned V-JEPA 2, optional

Evaluate:

- action probes
- IDM downstream performance
- FDM downstream performance
- throughput and memory
- per-game / per-category metrics

Promotion rule:

- only top VE candidates are used for expensive IDM/FDM sweeps.

## Phase 2: IDM ablations

Candidates:

- IDM-0: no-op / majority baseline
- IDM-1: action-prior baseline
- IDM-2: causal IDM
- IDM-3: non-causal IDM
- IDM-4: calibrated/filterable IDM
- IDM-5: per-game specialist IDM, optional

Ablations:

- VE candidate
- future offset τ
- context length
- K action slots
- mouse tokenization
- mask schedule
- iterative unmasking steps

Evaluate:

- offline IDM action reconstruction
- per-game / per-category metrics
- calibration
- pseudo-label distribution
- pseudo-label confidence vs correctness

Promotion rule:

- select best IDM candidate for pseudo-label generation based on validation pseudo-label usefulness proxy, not only token accuracy.

## Phase 3: Pseudo-label generation

Run selected IDM candidate(s) over pseudo-label subset.

Create:

- D_GT
- D_PSEUDO_ALL
- D_PSEUDO_FILTERED
- D_MIX

Validate:

- predicted MCAP can be evaluated
- pseudo-label confidence correlates with correctness
- pseudo-label distribution does not collapse to no-op
- pseudo-label quality is reported per game
- filtered labels improve validation-quality/coverage tradeoff

## Phase 4: FDM ablations

Candidates:

- FDM-0: no-op baseline
- FDM-1: previous-action repeat baseline
- FDM-2: ActionOnly transformer
- FDM-3: VideoOnly transformer
- FDM-4: FDM-GT
- FDM-5: FDM-Pseudo
- FDM-6: FDM-FilteredPseudo
- FDM-7: FDM-Mix
- FDM-8: FDM-GT with game ID, ablation
- FDM-9: FDM-Pseudo with game ID, ablation

Ablations:

- context length
- VE candidate
- GT vs pseudo labels
- filtered pseudo vs unfiltered pseudo
- GT/pseudo mixture ratio
- with vs without game ID
- model size
- action tokenization
- key/button state auxiliary target

Evaluate:

- offline teacher-forced metrics
- free-running-on-logged-video metrics
- per-game and per-category metrics
- held-out-game performance
- data scale trend

## Phase 5: Scale trend experiments

Run selected configurations on data scales:

```
1%
5%
10%
25%
50%
100%
```

Minimum configurations:

- best IDM candidate
- FDM-GT
- FDM-Pseudo
- FDM-FilteredPseudo
- FDM-Mix, if compute allows

Report:

- IDM quality vs data
- FDM-GT quality vs data
- FDM-Pseudo quality vs data
- Pseudo/GT ratio vs data
- held-out-game metrics vs data
- per-game macro-average vs data