# Evaluation

Canonical source: `../CANONICAL_SPEC.md`.

## Scope

This file defines evaluation metrics, aggregation rules, and the minimal required evaluation matrix. It should not duplicate model candidate recipes or training schedules; use `video_encoder.md`, `idm.md`, `fdm.md`, and `../ROADMAP.md` for those details.

Offline metrics select candidates. Logged free-running, harness stability, and FDM-1 target-gap evidence are required before making a final trained-model claim.

## 1. Common protocol

Use the same deterministic manifests, splits, tokenization config, and prediction-to-event conversion for all comparable runs.

Required protocol fields for every reported run:

- dataset root/revision and split manifest ID;
- git SHA, config path, container image digest, and checkpoint ID;
- train/validation/test split and held-out-game split;
- data scale subset (`10%`, `50%`, `100%`, plus optional smaller scales);
- action timebase: non-overlapping `50ms` bins;
- video-token source and feature-cache revision;
- action tokenizer revision and prediction-to-MCAP/event writer revision;
- seed(s), GPU count/type, and wall-clock/throughput summary.

All model predictions must be converted back to the canonical 50ms action/event representation before headline action metrics are computed.

## 2. Metric definitions

### 2.1 D2E primary action metrics

These are the headline IDM action metrics and the shared offline action-quality reference for FDM after prediction-to-event conversion. The implementation must match the D2E evaluator path whenever possible; if a wrapper is used, document the exact formula and any deviation.

- **Mouse Pearson X/Y:** Pearson correlation between predicted and ground-truth mouse deltas on each axis over evaluated 50ms bins. Report `NA` when an axis has zero variance and exclude `NA` from aggregate means with counts shown.
- **Mouse scale ratio X/Y:** predicted-to-ground-truth mouse magnitude/scale ratio per axis according to the D2E evaluator formula. Report both axes and flag extreme values caused by near-zero GT variance.
- **Mouse-button accuracy:** accuracy of mouse-button state/event predictions under the D2E evaluator schema.
- **Keyboard key accuracy:** key-state/key-event accuracy under the D2E evaluator schema.

### 2.2 Token and event diagnostics

Use these for model selection, failure analysis, and ablations. They are not substitutes for the D2E primary metrics.

- **Action-token NLL / cross-entropy:** mean negative log likelihood over supervised action tokens, reported by token family: mouse, keyboard, mouse button, scroll, `NO_ACTION`, and overflow/other where applicable.
- **Top-1 / top-k token accuracy:** optional diagnostic for discrete token heads; report by token family.
- **Sparse event precision/recall/F1:** event-level precision, recall, and F1 for keyboard, mouse buttons, and scroll events after prediction-to-event conversion.
- **No-op false-positive/false-negative rates:** false sparse actions during GT no-op bins and missed actions during GT active bins.
- **Impossible state rate:** invalid key/button transitions, stuck down states, duplicate releases, or other impossible state-machine outputs.
- **Dequantized mouse error:** L1/L2 error after converting mouse bins back to deltas; diagnostic only unless promoted by a written decision.

### 2.3 Video encoder metrics

Evaluate video encoders as representation candidates, not only as feature extractors.

- **Action probes:** frozen or fixed-budget probes for mouse, keyboard, mouse-button, scroll, and optional next-click targets.
- **Screen/game probes:** cursor/crosshair, HUD/UI/text/menu, low-motion state changes, and other screen-domain targets when available.
- **Downstream transfer:** fixed-budget Tiny-IDM and Tiny-FDM metrics using identical data, tokenization, and training budget.
- **Long-context compression:** tokens per 50ms bin, cache size per video-hour, supported context length, and metric degradation as context grows.
- **Adaptation safety:** pre/post adaptation comparison on held-out games and screen-state probes to catch overfitting or representation collapse.
- **Efficiency:** feature extraction FPS, GPU memory, training throughput, inference latency, and cache storage cost.

### 2.4 IDM-specific diagnostics

Use with the promoted masked diffusion IDM and relevant floor/diagnostic variants.

- masked-action NLL by diffusion noise level/timestep;
- sampler quality/throughput curve for `1/4/8/16` and optional `32` steps;
- calibration/ECE by diffusion step and final predicted token;
- high-confidence false positives;
- pseudo-label confidence/coverage curve;
- pseudo-label no-op/event-rate drift versus GT;
- future-visual policy diagnostics for `τ`, `C_future`, and window policy.

### 2.5 FDM-specific protocols and metrics

FDM must be evaluated causally: no visual evidence after decision time `t` may condition prediction of action bin `[t, t+50ms)`.

- **Teacher-forced offline metrics:** action-token NLL/CE, D2E action metrics after event conversion, sparse-event F1, no-op FP/FN, and per-game macro results.
- **Prediction-unit ablation metrics:** compare serialized intra-bin autoregression vs multi-head prediction using the same Tiny budget before Base promotion.
- **Pseudo-label usefulness metrics:** FDM-Pseudo/FDM-FilteredPseudo/FDM-Mix performance relative to FDM-GT, filtering coverage, and GT:pseudo mixture-ratio curves.
- **Logged free-running metrics:** feed predicted previous actions back while logged video remains fixed; report degradation over horizon, action spam, no-op collapse, key/button state violations, and mouse drift.
- **Harness stability metrics:** run duration, action count/rate, invalid action rate, stuck key/button incidents, cursor/mouse explosion or clipping, no-op collapse, crash/hang rate, and simple task/sanity success where available.
- **FDM-1 target-gap evidence:** public recipe/action-semantics alignment, comparable harness behavior categories, offline/free-running/harness evidence, and explicit non-comparable gaps.

### 2.6 Scaling metrics

For selected recipes only, report each primary metric versus data scale. Mandatory scales are `10%`, `50%`, and `100%`; `1%`, `5%`, and `25%` are optional when cheap or needed to explain curve shape.

## 3. Aggregation and reporting

Headline reports must include:

- **Micro-average:** aggregate over all eligible bins/events.
- **Per-game macro-average:** compute each metric per game, then average games equally.
- **Held-out-game macro-average:** same as per-game macro, restricted to held-out games.
- **Coverage:** number of recordings, bins, active-action bins, games, and retained pseudo-label tokens/bins when filtering is used.
- **Uncertainty:** bootstrap confidence intervals by recording or repeated-seed intervals where feasible; always report seed count.

Rules:

- Do not hide per-game regressions behind micro-average improvements.
- Report unweighted headline metrics even when weighted losses or balanced sampling are used for training.
- Keep `NA` metrics explicit with denominator counts.
- Report validation and test using the same metric code; test should be run only for selected checkpoints.
- Treat floor baselines as sanity checks, not final reproduction targets.

## 4. Minimal required evaluation matrix

| Stage | Required comparisons | Required metrics/protocols | Required aggregation |
| --- | --- | --- | --- |
| Data/evaluator sanity | GT round-trip and trivial floors | timestamp alignment, action distribution, event overflow, prediction-to-event round-trip | per recording and per game |
| Video encoder | frozen reference vs promoted adapted candidate(s) | action probes, screen/game probes, Tiny-IDM/Tiny-FDM transfer, long-context compression, efficiency, adaptation safety | micro, per-game macro, held-out-game macro |
| IDM | D2E-Generalist-IDM-1B reference vs promoted masked diffusion IDM; floors as diagnostics | D2E primary metrics, masked-diffusion diagnostics, calibration, sampler curve, future-window diagnostics | micro, per-game macro, held-out-game macro |
| Pseudo-labels | unfiltered vs filtered pseudo labels; optional Generalist-IDM pseudo labels if compatible | confidence/coverage, no-op/event drift, impossible state rate, downstream FDM usefulness | coverage curves plus held-out labeled validation |
| FDM offline | FDM-GT, FDM-Pseudo, FDM-FilteredPseudo, FDM-Mix, floor diagnostics | teacher-forced NLL/CE, D2E action metrics, sparse-event F1, no-op FP/FN, FDM-1 target-gap notes | micro, per-game macro, held-out-game macro |
| FDM ablations | serialized AR vs multi-head; active tokenization/filtering/mix ablations | same offline FDM metrics plus throughput and free-running stability where relevant | same split and budget for compared runs |
| Logged free-running | selected FDM checkpoints | horizon degradation, state violations, no-op collapse, action spam, mouse drift | per game/category and horizon |
| Harness stability | selected final checkpoint(s) | run duration, action count/rate, invalid actions, stuck states, drift/explosion, crashes, sanity success, FDM-1 target-gap evidence | per scenario plus aggregate summary |
| Scaling | selected IDM/FDM recipes only | primary metrics vs data scale, throughput/cost | fixed split policy and seed protocol |

## 5. Meaningful improvement rule

A result is meaningful only if it improves the relevant primary metric or target-gap evidence without hiding per-game macro regressions, calibration collapse, impossible action states, or harness instability. Failure cases and non-comparable closed-source gaps must be reported explicitly.
