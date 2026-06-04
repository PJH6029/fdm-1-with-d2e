# Roadmap

Canonical source: `CANONICAL_SPEC.md`; operational source: `OPERATIONAL_RULES.md`; metric/protocol source: `spec/evaluation.md`.

This file tracks execution progress for the D2E-based FDM-1 reproduction. It is a checklist, not a replacement for the component specs. Use it to mark implementation, ablation, evaluation, artifact, and decision progress phase by phase.

Legend:

- `[ ]` not started
- `[~]` in progress / partially complete
- `[x]` complete and verified
- `[!]` blocked or failed; explain in the phase notes

## Global tracking rules

- [ ] Every completed item links to a run record, config, metric JSON, checkpoint, report section, or explicit written decision.
- [ ] Main runs record git SHA, container image digest, MLXP reservation/run ID, W&B run, dataset manifest, split manifest, and config path.
- [ ] D2E source data remains read-only; derived artifacts are stored outside `/mnt/ddn/extra-ddn-continuous-gui/`.
- [ ] Base-scale runs are launched only after Tiny/baseline evidence justifies promotion.
- [ ] Failure cases are tracked instead of hidden behind aggregate metrics.

## Phase 0 — Data pipeline, evaluator, and sanity checks

Goal: build the deterministic D2E/action/evaluation foundation used by every later phase.

### Implementation

- [ ] D2E/OWAMcap reader loads labeled `.mkv` + `.mcap` recordings.
- [ ] Video frame/timestep sampler maps 60fps video to canonical 50ms bins.
- [ ] 50ms action binning aggregates mouse HID deltas, keyboard, buttons, and scroll events.
- [ ] Action tokenizer/de-tokenizer supports fixed mouse/event slots and special tokens.
- [ ] Prediction-to-MCAP/event writer round-trips model outputs into evaluator-compatible events.
- [ ] Split manifests are generated for train/validation/test and held-out-game splits.
- [ ] Scale manifests are generated for `10%`, `50%`, `100%` and optional `1%/5%/25%`.
- [ ] Per-game action distribution summaries are generated.

### Evaluation / sanity checks

- [ ] Video timestamps align with input events on sampled recordings.
- [ ] Keyboard/mouse overlay visualizations look plausible.
- [ ] Raw HID deltas reconstruct plausible movement.
- [ ] No-op/event distributions are logged by game and split.
- [ ] Event overflow is below threshold or explained.
- [ ] GT action round-trip passes evaluator and writer checks.

### References and floor checks

- [ ] D2E-Generalist-IDM-1B inference/evaluation path is located and versioned.
- [ ] IDM CE/MLM/no-op/action-frequency sanity paths are available only as floors/diagnostics.
- [ ] FDM no-op, previous-action, action-only, and video-only floor paths are available.
- [ ] Initial FDM-1 target-gap rubric draft is written from public claims and local harness categories.
- [ ] Frozen-encoder probe scaffold is available for domain-gap checks.

### Artifacts / decisions

- [ ] Dataset manifest ID:
- [ ] Split manifest ID:
- [ ] Action tokenizer revision:
- [ ] Evaluator revision:
- [ ] Phase 0 report section:

## Phase 1 — Video encoder domain-gap audit and gameplay adaptation

Goal: determine whether frozen pretrained video features are enough and, if not, adapt a video encoder toward D2E gameplay/screen representations.

### Implementation

- [ ] VE-0 frozen encoder bakeoff feature extraction works for practical candidates.
- [ ] VE-1 frozen encoder + temporal resampler reference works.
- [ ] Feature-cache format records source checkpoint, frame policy, token count, manifest, and git SHA.
- [ ] D2E gameplay adaptation path is implemented for VE-2 or VE-3.
- [ ] Optional screen/game auxiliary adaptation path is available if diagnostics justify it.
- [ ] Throughput, memory, latency, and cache-size logging is wired into runs.

### Ablation study

- [ ] Frozen encoder bakeoff compares practical pretrained candidates under identical probes.
- [ ] VE-1 tests whether a trainable temporal resampler over frozen features is enough.
- [ ] At least one VE-2 or VE-3 gameplay-domain adaptation is run unless VE-0/VE-1 unexpectedly pass held-out/downstream requirements.
- [ ] Optional VE-4 auxiliary adaptation is run only if UI/text/cursor/HUD failures are documented.

### Evaluation

- [ ] Action probes cover mouse, keyboard, buttons, scroll, and optional next-click targets.
- [ ] Screen/game probes cover cursor/crosshair, HUD/UI/text/menu, or other documented screen-state targets.
- [ ] Fixed-budget Tiny-IDM transfer is measured.
- [ ] Fixed-budget Tiny-FDM transfer is measured.
- [ ] Long-context compression reports tokens per bin, cache size per video-hour, supported context, and degradation.
- [ ] Adaptation safety compares pre/post adaptation on held-out games and screen-state probes.
- [ ] Operational efficiency reports extraction FPS, GPU memory, training throughput, inference latency, and cache storage cost.

### Promotion gate

- [ ] Promote at most 1-2 VE candidates for IDM/FDM.
- [ ] Promotion is based on held-out/downstream utility or documented screen/game perception failure fixes, not self-supervised loss alone.
- [ ] Promotion decision is recorded in `DECISIONS.md`.

## Phase 2 — IDM training and calibration

Goal: train a D2E masked diffusion IDM that can match or exceed the D2E-Generalist-IDM-1B reference and produce useful pseudo labels.

### Implementation

- [ ] D2E-Generalist-IDM-1B reference inference runs on the local split/evaluator path.
- [ ] IDM-CE one-shot classifier floor is implemented.
- [ ] IDM-MLM random-mask denoising floor is implemented.
- [ ] IDM-MDLM-16 masked discrete diffusion main candidate is implemented.
- [ ] IDM calibration/confidence export is implemented for pseudo-label filtering.
- [ ] Sampler supports `1/4/8/16` steps and optional `32`.
- [ ] Future visual context settings record `C_past`, `τ`, `C_future`, and window policy.

### Ablation study

- [ ] IDM-CE vs IDM-MLM vs IDM-MDLM-16.
- [ ] Causal vs non-causal IDM.
- [ ] `τ=0ms` vs `τ=100ms`.
- [ ] Future visual policy/width: anchor-start vs post-target and `C_future=50ms` vs `150ms`.
- [ ] Sampler steps `1/4/8/16`, plus `32` if compute allows.
- [ ] Context `2s` vs `10s` if throughput allows.
- [ ] Confidence filtering on/off.
- [ ] Optional IDM-MD4/SGMD, action-family schedules, or corrective/remasking only when diagnostics justify them.

### Evaluation

- [ ] D2E primary metrics compare promoted masked diffusion IDM to D2E-Generalist-IDM-1B.
- [ ] Micro, per-game macro, and held-out-game macro results are reported.
- [ ] Masked-action NLL by noise level/timestep is reported.
- [ ] Calibration/ECE by diffusion step and final token is reported.
- [ ] High-confidence false positives and impossible key/button states are analyzed.
- [ ] Pseudo-label confidence correlates with correctness on held-out labeled data.

### Promotion gate

- [ ] Promoted IDM is selected by D2E metrics against Generalist-IDM plus calibration and pseudo-label usefulness proxy.
- [ ] 16-step inference is reported as the FDM-1-aligned default; lower-step samplers remain speed/quality ablations.
- [ ] CE/MLM/prior variants are not promoted as the reproduction target.
- [ ] Promotion decision is recorded in `DECISIONS.md`.

## Phase 3 — Pseudo-label generation

Goal: create validated pseudo-label datasets for FDM training without modifying the source D2E dataset.

### Implementation

- [ ] `D_GT` is materialized from labeled data outside the source dataset tree.
- [ ] `D_PSEUDO_ALL` is generated from the promoted IDM.
- [ ] `D_PSEUDO_FILTERED` is generated from calibrated/confidence-filtered IDM predictions.
- [ ] `D_PSEUDO_GENERALIST_IDM` is generated only if D2E-Generalist-IDM-1B inference/output compatibility is practical.
- [ ] `D_MIX` recipes combine GT and pseudo labels with recorded ratios.
- [ ] Per-token and per-bin confidence summaries are materialized for FDM filtering ablations.

### Ablation study

- [ ] No filtering vs per-token confidence filtering/loss weighting.
- [ ] No filtering vs per-bin confidence filtering/loss weighting.
- [ ] Low-confidence handling: drop vs down-weight vs ignored-loss context retention.
- [ ] GT:pseudo mixture-ratio recipes are prepared.

### Evaluation

- [ ] Generated labels round-trip through evaluator/writer.
- [ ] Pseudo-label confidence/coverage curves are reported.
- [ ] Event/no-op distributions do not collapse or spam sparse events.
- [ ] Stuck key/button state risk is measured.
- [ ] Filtered labels improve or explain the quality/coverage tradeoff.

### Artifacts / decisions

- [ ] Pseudo-label dataset manifest IDs:
- [ ] Filtering threshold/coverage decision:
- [ ] Mixture-ratio candidate list:

## Phase 4 — FDM training and FDM-1 target-gap evaluation

Goal: train causal FDMs on GT, pseudo, filtered pseudo, and mixtures; quantify both offline quality and the gap to the closed-source FDM-1 FDM target.

### Implementation

- [ ] FDM enforces strict no-future-visual input alignment for action bin `[t, t+50ms)`.
- [ ] FDM-B0/B1/B2/B3 floor baselines/diagnostics are runnable.
- [ ] FDM-GT training is runnable.
- [ ] FDM-Pseudo training is runnable.
- [ ] FDM-FilteredPseudo training is runnable.
- [ ] FDM-Mix training is runnable.
- [ ] FDM-GeneralistIDM-Pseudo is runnable only if compatible.
- [ ] FDM-GameID remains optional and ablation-only.

### Ablation study

- [ ] Tiny FDM-SerializedAR and Tiny FDM-MultiHead run under identical tokenization, context, VE, and data budget.
- [ ] Better or complementary prediction-unit recipe is promoted to Base-scale runs.
- [ ] GT vs pseudo vs filtered pseudo vs mix.
- [ ] Per-token vs per-bin pseudo-label filtering/loss weighting.
- [ ] Low-confidence pseudo-label handling: drop vs down-weight vs ignored-loss context retention.
- [ ] GT:pseudo mixture-ratio sweep.
- [ ] Action-only vs video-only vs video+action.
- [ ] Short vs medium context (`2s` vs `10s`).
- [ ] Selected VE candidate comparison.

### Evaluation

- [ ] Teacher-forced NLL/CE by token family is reported.
- [ ] D2E-style action metrics after prediction-to-event conversion are reported.
- [ ] Sparse keyboard/button precision/recall/F1 is reported.
- [ ] No-op false-positive/false-negative rates are reported.
- [ ] Micro, per-game macro, and held-out-game macro results are reported.
- [ ] FDM-Pseudo/FDM-FilteredPseudo/FDM-Mix performance is compared relative to FDM-GT.
- [ ] FDM-1 target-gap rubric is applied; simple baseline wins are not treated as final reproduction success.

### Promotion gate

- [ ] Selected FDM checkpoint is justified by offline metrics, free-running readiness, and target-gap evidence.
- [ ] Prediction unit, token factorization, filtering policy, mixture ratio, and context length are recorded in `DECISIONS.md`.

## Phase 5 — Scaling curves

Goal: measure whether the selected recipes improve with D2E data scale.

### Implementation

- [ ] Scaling subsets are fixed and tied to deterministic manifests.
- [ ] Runs use the same selected recipe, metric code, and seed protocol across scales.

### Required scales

- [ ] `10%`
- [ ] `50%`
- [ ] `100%`

### Optional scales

- [ ] `1%` if cheap or needed for curve shape.
- [ ] `5%` if cheap or needed for curve shape.
- [ ] `25%` if the 10/50/100 curve is ambiguous.

### Minimum configurations

- [ ] Best promoted masked diffusion IDM.
- [ ] FDM-GT.
- [ ] Best pseudo-label FDM.
- [ ] FDM-Mix if competitive.

### Evaluation

- [ ] Primary metrics vs data scale plots are produced.
- [ ] Throughput/cost vs data scale is reported.
- [ ] Scaling failures or saturation are explained.

## Phase 6 — Logged free-running and harness stability

Goal: verify that the selected FDM checkpoint can run stable action sequences outside teacher forcing and provide behavioral FDM-1 target-gap evidence.

### Logged free-running

- [ ] Logged video remains fixed while model-predicted previous actions feed back into context.
- [ ] Horizon degradation is measured.
- [ ] Key/button state violations are measured.
- [ ] No-op collapse and action spam are measured.
- [ ] Mouse drift and movement-scale drift are measured.
- [ ] Per-game/category failures are reported.

### Harness implementation

- [ ] Deterministic desktop/game harness or replay-control harness is configured.
- [ ] Harness reset/snapshot or equivalent reproducibility mechanism is documented.
- [ ] Harness action logs are captured.
- [ ] Harness safety/postprocessing policy is fixed before final reporting.

### Harness evaluation

- [ ] Run duration and action count/rate are reported.
- [ ] Invalid action rate is reported.
- [ ] Stuck key/button incidents are reported.
- [ ] Cursor/mouse explosion or out-of-bounds drift is reported.
- [ ] Crash/hang rate is reported.
- [ ] Simple task/sanity success is reported where available.
- [ ] Qualitative/quantitative gap to comparable public FDM-1 task/behavior categories is documented where available.

### Promotion gate

- [ ] Harness results support stable action execution rather than smoke-only execution.
- [ ] Remaining FDM-1 non-comparable gaps are explicit.
- [ ] Harness inference and safety policies are recorded in `DECISIONS.md`.

## Phase 7 — Final report and artifact package

Goal: make the reproduction rerunnable and scientifically interpretable.

### Required artifacts

- [ ] Exact configs and commands.
- [ ] Dataset, split, and scale manifests.
- [ ] Git SHA and container image digest.
- [ ] MLXP reservation/run records.
- [ ] W&B run links and metrics JSON.
- [ ] Training logs.
- [ ] Checkpoints.
- [ ] Feature-cache manifests.
- [ ] Video encoder probe/downstream/efficiency tables.
- [ ] IDM metrics against D2E-Generalist-IDM-1B.
- [ ] Pseudo-label quality/coverage tables.
- [ ] FDM offline/free-running/harness metrics.
- [ ] Ablation and scaling plots.
- [ ] Failure analysis and limitations.

### Report outline

- [ ] Motivation and relation to public FDM-1/D2E.
- [ ] Dataset, splits, tokenization, and reproducibility setup.
- [ ] Video encoder survey/domain-gap/adaptation results.
- [ ] IDM method and masked diffusion ablations.
- [ ] Pseudo-label generation and calibration.
- [ ] FDM method and FDM-1 target-gap analysis.
- [ ] Harness stability evidence.
- [ ] Scaling curves.
- [ ] Failure analysis, closed-source assumptions, and future work.
