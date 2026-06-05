# Canonical Reproduction Spec: FDM-1 with D2E

Status: canonical planning spec as of 2026-06-05.
Scope: serious research reproduction, not a smoke path or demo-only PoC.

## 1. External anchors and closed-source gap

Public FDM-1 describes a three-stage recipe: train an inverse dynamics model (IDM) on labeled screen recordings, use the IDM to pseudo-label much larger video-only corpora, then train a forward dynamics model (FDM) autoregressively on interleaved video/action data. Publicly disclosed IDM details indicate a non-causal masked-action model trained with a diffusion masked objective and decoded with a 16-step noise schedule. Publicly disclosed action-token details include key press/release tokens, scroll tokens, mouse deltas split into X/Y and normalized before 49-way exponential binning, and an auxiliary next-click-position prediction target.

D2E provides synchronized 480p/60fps gameplay video, audio, keyboard events, mouse clicks/coordinates/raw HID deltas, and OWAMcap/MCAP logs. The D2E project also publicly released Generalist-IDM-1B weights and inference code. The D2E public evaluation protocol computes standardized action metrics over non-overlapping 50ms bins: mouse Pearson correlation X/Y, mouse scale ratio X/Y, mouse-button accuracy, and keyboard key accuracy.

The exact FDM-1 architecture, training schedules, dataset mixture, confidence filtering, context lengths, video encoder details, FDM checkpoint, and online harness are closed source. Public video-encoder evidence also suggests that common pretrained encoders are mostly natural/web-video, action-recognition, video-text, or physical-world models rather than gameplay/screen-recording specialists. This reproduction therefore treats gameplay-domain video representation learning as a core research problem, treats FDM-1's FDM as the ultimate target, uses public FDM-1 claims and behavior categories as target evidence where direct comparison is impossible, and records every assumption, ablation, gap, and failure mode.

## 2. Objective

Build a reproducible D2E training and evaluation pipeline that produces trained checkpoints and a report showing whether an FDM-1-style Video Encoder → IDM → pseudo-labeling → FDM recipe works on real D2E data.

A completed reproduction must show all of the following:

1. **IDM quality:** a D2E-trained masked discrete diffusion IDM matches or exceeds the public D2E Generalist-IDM-1B reference on the same D2E-standard 50ms action metrics, split policy, and prediction-to-MCAP evaluation path.
2. **Video encoder domain adaptation:** the video encoder learns a D2E gameplay/screen representation that preserves HUD/UI/cursor/crosshair/control-relevant state, generalizes to held-out games, and compresses long contexts efficiently. Frozen generic video encoders are diagnostic initializations, not assumed-sufficient solutions.
3. **Pseudo-label usefulness:** FDMs trained from IDM pseudo-labels retain a substantial fraction of GT-label FDM performance, and filtering/calibration improves the pseudo-label quality/coverage tradeoff.
4. **FDM quality:** the trained FDM aims to match the closed-source FDM-1 FDM as the ultimate reproduction target. Because FDM-1 weights and exact eval harness are not public, report a FDM-1 target-gap analysis using comparable public claims, logged D2E action metrics, free-running stability, and harness behavior.
5. **Stability:** the selected trained FDM runs in a desktop/game harness or replay-control harness with stable action sequences, no stuck key/button states, no mouse explosion, and bounded no-op collapse.
6. **Reproducibility:** the pipeline, container, exact configs, dataset manifests, metrics JSON, training logs, checkpoints, and final report are sufficient to rerun the main results.

## 3. Non-goals and claim boundaries

- The ultimate target is to match FDM-1's FDM behavior/performance envelope, but do not claim achieved exact parity with the closed-source model or Standard Intelligence's private 11M-hour corpus unless direct evidence supports it.
- Direct CE/MLM IDMs, causal IDMs, and no-op/action-frequency priors are sanity/floor ablations only; they are not the IDM reproduction target. Simple FDM baselines such as no-op, previous-action, action-only, and video-only are floor/diagnostic checks, not the FDM reproduction target.
- Do not assume a generic pretrained video encoder has sufficient gameplay/screen-recording domain knowledge; frozen encoders must be audited as baselines/initializations.
- Do not train a custom internet-scale video encoder from scratch unless later evidence makes it necessary; prioritize D2E gameplay-domain adaptation of strong pretrained initializations.
- Do not modify the D2E source dataset. Treat `/mnt/ddn/extra-ddn-continuous-gui/` as read-only input.
- Audio, transcripts, language grounding, and robot transfer are out of the first canonical reproduction unless promoted by a later written decision.
- Online game solving is not the primary model-selection metric, but a harness stability demonstration is required for the final reproduction claim.

## 4. Dataset contract

Use the MLXP-mounted D2E dataset:

```text
/mnt/ddn/extra-ddn-continuous-gui/
  labeled/<game-name>/<recording>.mkv|.mcap
  unlabeled/<game-name>/<video>.mkv
  */.source-metadata/   # provenance only; not training input
```

Required manifests:

- exact dataset root, recording list, duration, game name, split, and checksum/size metadata;
- train/validation/test split over recordings;
- held-out-game split for cross-game generalization;
- deterministic data-scale subsets;
- per-game action distributions, no-op rates, raw mouse magnitude distributions, and event-overflow rates.

Default split policy:

- **In-game split:** train/val/test recordings for every game with enough labeled data.
- **Held-out-game split:** reserve representative games from 2D, 3D/FPS, open-world/sandbox, and UI/menu-heavy categories.
- **Scale subsets:** 10%, 50%, 100% are mandatory for scaling curves; 1% and 5% are optional debug/low-scale points if cheap.

## 5. Canonical timebase and action representation

- Use non-overlapping **50ms bins** as the canonical action timestep.
- Sample or pool video to one visual timestep per 50ms bin from the 60fps D2E video.
- Aggregate raw HID mouse deltas inside each bin.
- Use a fixed action serialization per bin:

```text
MOUSE_MOVE_BIN_<xbin>_<ybin>
EVENT_SLOT_1
...
EVENT_SLOT_K
```

Defaults:

- `K = 8` sparse event slots per bin.
- Compound mouse token with 49 signed exponential bins per axis (`49 x 49` movement tokens).
- Keyboard tokens: `KEY_DOWN_<key>`, `KEY_UP_<key>`.
- Mouse button tokens: left/right/middle down/up.
- Scroll tokens: directional scroll first; magnitude bins only if needed.
- `NO_ACTION` fills unused event slots; `PAD_ACTION` is for sequence packing only; `EVENT_OVERFLOW` is logged and should stay below 0.1% of bins.
- Auxiliary click head: predict the next click location within a short horizon; do not make it a required action token.

Ablate only when a failure justifies it: `K ∈ {4, 8, 16}`, compound vs separate-axis mouse tokens, click grid size, and event-overflow policy.

## 6. Pipeline

```text
D2E labeled/unlabeled recordings
  → data reader + 50ms action binning + tokenization
  → video encoder bakeoff + D2E gameplay-domain adaptation + feature cache
  → IDM training on labeled recordings
  → IDM pseudo-labeling of unlabeled/video-only recordings
  → FDM training on GT, pseudo, filtered pseudo, and mixtures
  → offline metrics + logged free-run metrics + harness stability
  → report + checkpoints + reproducible configs
```

Before expensive component ablations, build a thin end-to-end integration spine after the data/evaluator foundation is in place. The spine should run a tiny/fixture path through D2E reading, tokenization, a minimal frozen/stub VE feature path, Tiny IDM train/infer, pseudo-label materialization, Tiny FDM train/infer, prediction-to-event conversion, and evaluator/reporting outputs. This is an engineering compatibility gate, not a model-quality gate: it may use tiny models or stub/frozen components, but it must prove schema compatibility, artifact paths, no-future-visual FDM alignment, evaluator invocation, run-record completeness, and reproducible `uv run ...` commands before later VE/IDM/FDM ablations scale up.

The spine must be contract-driven rather than a monolithic shortcut. Stage-specific logic belongs in reusable package modules, committed configs, schemas, and artifact formats so later phase implementations can replace stub/tiny components behind the same interfaces. Phase 0.5 stub, tiny, or naive implementations are compatibility fixtures only; they do not complete or promote the later VE, IDM, pseudo-labeling, or FDM research objectives unless those later phase gates separately audit and justify them.

## 7. Model families

### 7.1 Video encoder

The main video-encoder research question is whether a strong pretrained video model can be adapted into a D2E gameplay/screen-recording representation. Frozen generic encoders are expected to be domain-mismatched until proven otherwise; they are baselines and initializations, not the main solution.

- **VE-0 Frozen encoder bakeoff:** compare V-JEPA 2/2.1, VideoPrism, VideoMAE/InternVideo-style candidates when available, using D2E action probes and Tiny-IDM/Tiny-FDM transfer. Diagnostic only.
- **VE-1 Frozen encoder + temporal resampler:** tests whether token selection/compression over frozen features is enough. This is the frozen reference, not the expected final recipe.
- **VE-2 D2E gameplay adapter/LoRA/last-block adaptation:** main practical adaptation candidate for HUD/UI/cursor/crosshair/game-state domain knowledge.
- **VE-3 D2E self-supervised gameplay adaptation:** main representation-learning candidate using masked latent/video prediction on D2E recordings before IDM/FDM training.
- **VE-4 Screen/game auxiliary adaptation:** optional if diagnostics show UI/text/cursor/HUD failures; add auxiliary probes/losses for screen-specific state.

VE-2 or VE-3 should be attempted unless VE-0/VE-1 unexpectedly match downstream held-out-game requirements.

### 7.2 IDM

- **D2E-Generalist-IDM-1B Reference:** public D2E Generalist-IDM checkpoint and inference code. This is the primary IDM reference objective: evaluate it on the exact same local splits, timebase, and MCAP/evaluate.py-compatible path used for our IDM. Because this public model may have trained on overlapping D2E recordings, label it as a public target/reference rather than a clean held-out baseline unless the overlap is audited.
- **IDM-MDLM-16 Main:** non-causal masked discrete diffusion IDM. Video/context tokens stay visible; target action slots are corrupted with absorbing `MASK_ACTION`; the denoiser is conditioned on a sampled timestep/noise level; training uses weighted masked-token CE under a diffusion schedule; inference starts from fully masked target slots and uses a 16-step confidence-guided sampler.
- **IDM-MD4/SGMD:** continuous-time or state/action-dependent masked diffusion candidate, promoted only if IDM-MDLM-16 underperforms or calibration/no-op-collapse diagnostics justify it.
- **IDM-ActionSchedule:** action-family masking/sampling/loss schedule ablation for no-op, mouse movement, keyboard/button/scroll, and invalid-state control.
- **IDM-Corrective/Remask:** correction-oriented training or sampler remasking for high-confidence false positives, stuck keys/buttons, or visible wrong-token failures.
- **IDM-CE and IDM-MLM:** one-shot cross-entropy classifier and random-mask denoising floors. Use for sanity checks, initialization, and ablation only; do not treat them as the reproduction target.
- **IDM-Calibrated:** temperature/confidence/entropy-filtered version of the promoted IDM used for pseudo-labeling.
- **IDM-Sanity Priors:** no-op/zero-mouse/action-frequency priors. These are implementation sanity checks only and must not be used as the success objective.
- **IDM-Causal Ablation:** past-video-only ablation to quantify the value of non-causal inverse dynamics. It is an ablation, not the target baseline.
- **IDM-Specialist:** per-game specialist only as an upper-bound diagnostic, not the main result.

Default non-causal future offset is `τ = 100ms`; ablate `0ms` vs `100ms` first, then add `50/150/200ms` only if needed. `τ` is the future visual evidence offset/anchor, not the full context length. Future visual width is `C_future`; each IDM run must record the actual past/future frame span, token count, temporal-resampler settings, and future-window policy. Ablate anchor-start `[t+τ, t+τ+C_future)` vs post-target `[t+50ms, t+50ms+C_future)` first with `C_future=50ms` vs `150ms`; add anchor-centered windows only if the first sweep is ambiguous.

### 7.3 FDM

Avoid naming local candidates `FDM-1`, because that collides with the public model name.

Target/reference:

- **FDM-1 FDM Target:** the closed-source FDM-1 forward dynamics/action model is the ultimate reproduction target. There is no public checkpoint, so comparisons must be framed as target-gap evidence: public FDM-1 recipe/claim alignment, D2E offline action quality, logged free-running stability, harness behavior, and limitations caused by D2E's smaller data volume.

Input alignment rule:

- **No future visual evidence:** when predicting action bin `A_t = [t, t+50ms)`, FDM may condition only on visual tokens available at decision time `t` and previous actions `A_<t`. `VideoBin_t` is allowed only if it is defined from frames ending at or before `t`; otherwise use `VideoBin_<t` or re-index the visual bin to avoid target-interval leakage.

Floor baselines and diagnostics:

- **FDM-B0 No-op/zero-mouse floor**
- **FDM-B1 Previous-action repeat floor**
- **FDM-B2 Action-only transformer diagnostic**
- **FDM-B3 Video-only transformer diagnostic**

Prediction-unit candidates:

- **FDM-SerializedAR:** predicts mouse/event slots inside the target 50ms bin autoregressively.
- **FDM-MultiHead:** predicts mouse movement and event slots with independent heads from the same causal hidden state.

Main trained candidates:

- **FDM-GT:** video + past GT actions, trained on GT labels.
- **FDM-Pseudo:** video + IDM pseudo-labels, trained on unfiltered pseudo-labels.
- **FDM-FilteredPseudo:** trained on calibrated/confidence-filtered pseudo-labels, with per-token vs per-bin filtering/loss-weighting and low-confidence drop/weight/ignore policies treated as ablations.
- **FDM-Mix:** trained on GT + pseudo-label mixture; sweep GT:pseudo ratios rather than fixing one default.
- **FDM-GeneralistIDM-Pseudo:** optional comparison trained on D2E-Generalist-IDM-1B pseudo-labels only if inference/output compatibility is practical.
- **FDM-GameID:** optional ablation, not the headline, because game ID can hide weak cross-game generalization.

## 8. Evaluation spec

Keep headline metrics small and reproducible. Diagnostic metrics may be logged, but they should not multiply headline claims.

### 8.1 Video encoder primary metrics

The video encoder should learn a compact gameplay/screen-recording representation that preserves control-relevant state, generalizes across games, and supports long video contexts. Evaluate frozen and adapted VE candidates by:

1. **Game-state representation:** action probes and screen-specific probes for mouse, keyboard, mouse buttons, cursor/crosshair, HUD/UI/text, and optional next-click targets.
2. **Generalization:** per-game macro and held-out-game probe/downstream metrics, not only micro-average or in-game validation.
3. **Long-context compression:** tokens per 50ms bin, cache size per video-hour, supported context length, and degradation as context grows.
4. **Downstream utility:** fixed-budget Tiny-IDM/Tiny-FDM transfer under identical data, tokenization, and training budget.
5. **Efficiency:** feature extraction throughput, GPU memory, training throughput, and inference latency.

Promote an adapted VE only if it improves held-out or downstream action metrics, or fixes a documented screen/game perception failure, without making 50%/100% scale runs infeasible. Do not promote a VE solely because its self-supervised loss improves.

### 8.2 IDM primary metrics

Use the D2E 50ms-bin metrics as headline and compare the promoted masked diffusion IDM to D2E-Generalist-IDM-1B on the same split/evaluator path:

1. mouse Pearson correlation X/Y;
2. mouse scale ratio X/Y;
3. mouse-button accuracy;
4. keyboard key accuracy.

Report micro-average, per-game macro-average, and held-out-game macro-average. Also log diffusion and pseudo-label diagnostics for model selection and failure analysis, but do not make them headline claims unless explicitly studying calibration:

- masked-action NLL by noise level/timestep;
- per-action-family NLL, accuracy, precision/recall/F1;
- calibration/ECE by diffusion step and final token;
- sampler step quality/throughput curve for `1/4/8/16` and `32` if compute allows;
- high-confidence false positives, no-op/event-rate distribution, and impossible key/button state rate.

### 8.3 FDM primary metrics

FDM evaluation has two levels: (1) a target-gap analysis against the public FDM-1 FDM goal, and (2) D2E offline/floor-baseline metrics used to make the comparison reproducible.

FDM-1 target-gap evidence:

- alignment with the public FDM-1 training recipe and action-token semantics;
- ability to run stable action sequences in desktop/game or replay-control harnesses;
- comparison to public FDM-1 task/behavior categories where a comparable local harness exists;
- explicit gap analysis for data scale, model scale, missing transcripts/language grounding, and closed-source eval differences.

For teacher-forced held-out D2E evaluation:

1. next-action NLL / cross-entropy by token family;
2. D2E-style action metrics after converting predictions to MCAP-like events;
3. sparse event precision/recall/F1 for keyboard and mouse buttons;
4. no-op false-positive/false-negative rates;
5. per-game macro-average and held-out-game macro-average.

For logged free-running evaluation:

- feed the model's predicted previous actions back while keeping logged video fixed;
- report degradation over horizon, key/button state violations, no-op collapse rate, and mouse drift.

For harness stability:

- run the selected checkpoint in a deterministic desktop/game harness or replay-control harness;
- report sequence length, action rate, invalid-action rate, stuck-key/button incidents, cursor/mouse drift bounds, crash rate, and task/sanity success where available.

### 8.4 Meaningful improvement rule

A result counts as a meaningful win only when:

- VE candidates are judged by gameplay/screen representation quality, held-out-game generalization, long-context compression, downstream action-model utility, and efficiency;
- IDM is a masked diffusion model by default and is compared against the D2E-Generalist-IDM-1B public reference; CE/MLM/prior variants are floors or ablations only;
- FDM is evaluated against the FDM-1 target-gap rubric, with simple FDM baselines treated only as floor checks;
- the model improves reproducible primary aggregate metrics without hiding per-game macro regressions;
- bootstrap confidence intervals or repeated-seed intervals exclude zero improvement when feasible;
- failure cases are reported instead of hidden.

Avoid hard-coded absolute offline thresholds before measuring dataset difficulty, floor-baseline behavior, and feasible FDM-1 target-gap evidence. Pre-register relative deltas and target-gap criteria after the first measurement pass.

## 9. Ablation and scaling budget

Do not run a full factorial grid. Use a staged promotion protocol:

1. Run cheap data/eval/baseline checks on small subsets.
2. Use Tiny models for broad sweeps.
3. Promote only the best 1–2 settings to Base models.
4. Run final scaling curves only on selected configurations.

Mandatory ablations:

- VE: frozen encoder bakeoff and VE-1 frozen-resampler reference; VE-2/VE-3 gameplay-domain adaptation as main candidates unless frozen features unexpectedly satisfy held-out/downstream requirements.
- IDM: D2E-Generalist-IDM-1B reference; IDM-CE and IDM-MLM as floor objective ablations; IDM-MDLM-16 as the main masked diffusion objective; causal vs non-causal; `τ=0ms` vs `τ=100ms`; future visual policy/width anchor-start vs post-target and `C_future=50ms` vs `150ms`; sampler steps `1/4/8/16` and `32` if compute allows; confidence filtering on/off. Add anchor-centered future windows, IDM-MD4/SGMD, action-family schedules, and corrective/remasking only when diagnostics justify them.
- Tokenization: compound mouse token vs separate X/Y only if sparsity or NLL indicates a problem.
- FDM: FDM-1 target-gap analysis; strict no-future-visual input alignment; no-op/previous-action/action-only/video-only as floors/diagnostics; `FDM-SerializedAR` vs `FDM-MultiHead` on Tiny before Base promotion; GT, pseudo, filtered pseudo, and mix as trained candidates; per-token vs per-bin pseudo filtering, low-confidence handling, and GT:pseudo mixture-ratio sweeps.
- Context: short vs medium (`2s/10s` first; longer only after throughput is proven).
- Scale: 10%, 50%, 100% mandatory; 1%/5% optional; 25% optional if curve shape is ambiguous.

## 10. Success gates

### Gate 0 — Data and evaluation reproducibility

- D2E reader works for labeled recordings.
- 50ms action binning reconstructs plausible keyboard/mouse overlays.
- Official-style metrics run from predictions and GT MCAP/logs.
- Split and scale manifests are committed.

### Gate 0.5 — Thin end-to-end integration spine

- A single config/CLI path runs the tiny spine from D2E reader/tokenization through VE features, Tiny IDM train/infer, pseudo-label materialization, Tiny FDM train/infer, prediction conversion, and evaluator/reporting outputs.
- The E2E CLI is a thin orchestrator over reusable component modules/configs rather than an inline monolithic script.
- Explicit component contracts exist for tokenized data, VE cache, IDM predictions, pseudo labels, FDM predictions, evaluator inputs, and evaluator outputs.
- Local fixture/unit/integration tests validate schema compatibility across tokenizer, VE cache, IDM output, pseudo-label dataset, FDM input/output, and evaluator input.
- Contract tests show stub/tiny components can be replaced by later serious implementations without changing downstream artifact consumers.
- If real D2E data is needed for interface validation, a tiny MLXP run is recorded with git SHA, config, `uv run ...` command, artifact paths, and environment details.
- Generated outputs, caches, pseudo labels, checkpoints, reports, and temp files are written outside the source dataset tree.
- FDM visual-bin indexing passes a no-future-visual-leakage guard.
- Gate 0.5 results are compatibility/test evidence only; stub/tiny implementations must not be treated as completing or promoting later VE/IDM/pseudo-label/FDM phase objectives.

### Gate 1 — Gameplay-domain video representation

- Frozen pretrained encoders are audited as domain-gap baselines rather than assumed sufficient.
- VE candidates have deterministic feature caches tied to manifest, git SHA, and config.
- Probe metrics cover action state plus screen/game-specific state such as cursor/crosshair, HUD/UI/text, and next-click where feasible.
- At least one D2E gameplay-domain adaptation path (adapter/LoRA/last-block or self-supervised masked latent/video adaptation) is evaluated unless frozen features already meet held-out/downstream requirements.
- Promoted VE candidates improve downstream validation or held-out-game action metrics, or clearly fix a documented screen/game perception failure, without making scale runs infeasible.

### Gate 2 — IDM useful labeler

- D2E-Generalist-IDM-1B is evaluated as the primary public reference on the same local splits and evaluator path.
- IDM-MDLM-16 or a promoted masked diffusion variant matches or exceeds D2E-Generalist-IDM-1B on the D2E primary metrics; if it does not, the gap is quantified and treated as a reproduction failure/limitation rather than hidden behind direct CE/MLM, causal, or prior baselines.
- 16-step inference is the default reported diffusion setting; lower-step samplers are speed/quality ablations.
- Calibration/confidence correlates with correctness.
- Pseudo-label distribution does not collapse to no-op, stuck keys/buttons, or impossible key/button states.

### Gate 3 — Pseudo-label dataset

- Pseudo labels are generated reproducibly for the selected unlabeled/video-only subset.
- Filtered pseudo labels show a measurable quality/coverage tradeoff.
- Generated labels can round-trip through the evaluator and visualizer/harness tools.

### Gate 4 — FDM target-gap and offline result

- The report defines a FDM-1 target-gap rubric from public FDM-1 claims, action semantics, and locally reproducible harness categories.
- FDM-GT and pseudo-label FDMs are evaluated against that rubric; any gap to FDM-1 is quantified rather than hidden.
- FDM-GT beats simple floor baselines; this is required but not sufficient for the reproduction claim.
- FDM-Pseudo or FDM-FilteredPseudo beats action-only/video-only diagnostics and retains a substantial fraction of FDM-GT performance.
- FDM-Mix improves or explains why mixing fails.
- Held-out-game and per-category results are reported.

### Gate 5 — Stability result

- Selected FDM checkpoint executes stable action sequences in the harness.
- Failures such as stuck keys, mouse explosions, no-op collapse, event spam, or latency instability are quantified.

### Gate 6 — Final artifact package

- Checkpoints, configs, container tag/digest, run commands, metrics JSON, dataset manifests, logs, and report are preserved.
- The report includes method, baseline comparison, ablations/scaling curves, failure analysis, and reproducibility instructions.

## 11. Required report outline

1. Motivation and relation to public FDM-1/D2E.
2. Closed-source assumptions and reproduction decisions.
3. Dataset/splits/tokenization.
4. Video encoder, IDM, pseudo-labeling, and FDM methods.
5. Targets, references, and floor baselines.
6. Video encoder domain-gap audit, adaptation, long-context compression, and downstream evaluation.
7. Offline IDM metrics versus D2E-Generalist-IDM-1B.
8. Pseudo-label usefulness.
9. Offline FDM metrics and FDM-1 target-gap analysis.
10. Logged free-run and harness stability results.
11. Ablation/scaling curves.
12. Failure analysis.
13. Reproducibility package and exact commands.

## 12. Sources

- D2E project/GitHub: <https://github.com/worv-ai/D2E>
- Generalist-IDM-1B model: <https://huggingface.co/open-world-agents/Generalist-IDM-1B>
- D2E paper: <https://arxiv.org/abs/2510.05684>
- FDM-1 public post: <https://si.inc/posts/fdm1/>
