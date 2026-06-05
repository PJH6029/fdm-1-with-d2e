# Reproduction Decisions Register

Canonical source: `./CANONICAL_SPEC.md`. Record final decisions here as they are made. Do not leave major decisions implicit in code.

## Data decisions

- D2E dataset revision / local manifest ID: Phase 0 uses MLXP D2E root `/mnt/ddn/extra-ddn-continuous-gui` as read-only input; local labeled manifest `phase0-dataset-75ae762b7c5aed63` contains 459 labeled `.mkv`/`.mcap` pairs across 29 games (`notes/runs/20260605-phase0-real-d2e-mlxp-smoke.md`).
- Exact game list and categories: exact 29-game list is stored in `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/artifacts/dataset_manifest.json`; category labels are deferred until a later evaluation/reporting story needs them.
- Train/val/test split policy: deterministic per-game split with seed `0` and fractions train/validation/test `0.8/0.1/0.1`; Phase 0 manifest `phase0-split-56832b5d5d8c31e6` yields train `367`, validation `46`, test `46`; underfilled games are recorded in the split artifact.
- Held-out-game split: no held-out games selected in Phase 0 (`held_out_test=0`); later cross-game evaluation phases must make an explicit held-out-game decision before claiming held-out-game macro results.
- Scale subset construction: deterministic nested subsets from the train split, stratified by game when a dataset manifest is available; Phase 0 scale manifest `phase0-scale-726895836126a6ef` includes `5%` (`36`), `10%` (`50`), `50%` (`193`), and `100%` (`367`) train recordings.
- Menu/loading/inactive segment policy: retain all recorded segments in Phase 0 manifests and action distributions; any menu/loading/inactive filtering must be a later explicit decision with before/after distribution evidence.
- Audio policy: out of first canonical scope unless promoted.
- Active window metadata policy: decode/track screen/input topics for diagnostics, but ignore `window`, `keyboard/state`, and `mouse/state` as model-training inputs in Phase 0 action distributions; future auxiliary-state use requires a separate decision.

## Tokenization decisions

- Timebase: `50ms` bins.
- Sparse event slots: default `K=8`.
- Mouse tokenization: default 49x49 compound signed exponential bins.
- Mouse bin fitting data: Phase 0 uses the fixed default signed exponential quantizer (`max_abs_delta=4096`) rather than fitting bins from data; train-split fitting remains an optional later ablation decision.
- Scroll representation: directional sparse event tokens (`SCROLL_UP`, `SCROLL_DOWN`, `SCROLL_LEFT`, `SCROLL_RIGHT`) from raw scroll deltas; pinned official D2E `evaluate.py` does not score scroll, so G015 tokenized writer skips scroll and records skipped count.
- Click-position auxiliary grid/horizon: deferred; no Phase 0 auxiliary click-position target.
- Key/button state auxiliary targets: deferred; Phase 0 tokenizer represents press/release events only, while state topics are ignored for training input.
- Overflow threshold/action: keep the spec threshold of `0.1%` overflow bins before increasing `K`; tokenizer preserves mouse buttons, then key-down, then key-up, emits `EVENT_OVERFLOW` for excess events, and logs overflow. Phase 0 real-D2E one-per-game action distribution observed overflow `0.0`; G015 tokenized writer observed `0` overflow bins on Apex.

## Video encoder decisions

- Pretrained encoder/checkpoint candidates:
- Frozen encoder domain-gap conclusion:
- Feature-cache format and path:
- Tokens per bin:
- Frozen-resampler reference result:
- Gameplay adaptation path selected (adapter/LoRA/last-block/self-supervised):
- Domain adaptation objective:
- Screen/game auxiliary targets, if used:
- Whether downstream training finetunes encoder:
- Video encoder promotion metric/rubric:
- Action/screen probe heads/targets:
- Long-context compression target:
- Feature cache budget:
- Adaptation safety checks:

## IDM decisions

- D2E-Generalist-IDM-1B reference checkpoint/revision: public model id `open-world-agents/Generalist-IDM-1B`; pinned D2E reference repo commit `80e98e26e4dc584ec76fec5789b4a97c275dd032`.
- Generalist-IDM inference command/path: official `inference.py` path located in pinned D2E repo artifact under `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/official_d2e_repo/`; actual Generalist-IDM inference is deferred to Phase 2.
- Generalist-IDM evaluation compatibility notes: pinned official `evaluate.py` accepts `ground_truth.mcap predicted.mcap`, aligns on first `screen` `media_ref.pts_ns`, and scores `screen`, `keyboard`, `mouse/raw` in non-overlapping 50ms bins. Phase 0 verified same-MCAP official scoring and writer-produced MCAP scoring on Apex; exact writer metrics were perfect, tokenized writer metrics were high with expected mouse quantization loss.
- Main IDM objective:
- Past context length `C_past`:
- Future offset `τ`:
- Future width `C_future`:
- Future-window policy (anchor-start / post-target / anchor-centered):
- Initial future-context ablation (`τ=0/100ms`, `C_future=50/150ms`, anchor-start vs post-target):
- Diffusion mask/noise schedule:
- Sampler step (`1/4/8/16`, optional `32`):
- Confidence/calibration method:
- Filtering thresholds and coverage:
- Generalist vs specialist policy:

## FDM decisions

- FDM-1 target-gap rubric: Phase 0 draft rubric `phase0-fdm1-target-gap-rubric-draft-v0` in `notes/experiments/20260605-phase0-fdm1-target-gap-rubric-draft.md`; this is non-final and cannot support reproduction success claims without later FDM/free-running/harness evidence.
- Public FDM-1 task/behavior categories used for comparison:
- Local harness scenarios mapped to FDM-1 claims:
- Known non-comparable FDM-1 gaps:
- FDM causal input alignment / visual cutoff:
- FDM prediction unit selected (SerializedAR / MultiHead):
- FDM action token factorization selected:
- Context length:
- Model size:
- Loss weights:
- Class imbalance handling:
- Pseudo-label filtering policy (per-token / per-bin / none):
- Low-confidence pseudo-label handling:
- GT/pseudo mixture ratio:
- Game ID usage:
- Action chunk prediction policy:
- Harness inference sampling/decoding policy:
- Harness safety/postprocessing policy:

## Evaluation decisions

- Primary aggregate metric/composite: no single composite selected in Phase 0; report official D2E primary metrics individually (mouse Pearson X/Y, mouse scale ratio X/Y, mouse-button accuracy, keyboard key accuracy) and retain per-game/held-out aggregation decisions for later model-evaluation phases.
- Bootstrap/repeated-seed protocol:
- Harness type and scenarios:
- Reported failure categories:
- Criteria for promoting optional ablations:

## Operational decisions

- Docker image tag/digest: Phase 0 final data/evaluator smoke image `docker.io/pjh6029/fdm-1-with-d2e:phase0-20260605-ee08fb8@sha256:4b6d2e78f8f6393ca0e8b23af21de50fc852c292cdd2c934cb2a05f31d6555cb`; earlier G009 image is recorded in `notes/runs/20260605-phase0-real-d2e-mlxp-smoke.md`.
- MLXP reservation/run record location: Phase 0 production reservations and cancellation evidence are recorded under `notes/runs/20260605-phase0-real-d2e-mlxp-smoke.md`, `notes/runs/20260605-phase0-g015-writer-produced-mcap-roundtrip.md`, `notes/runs/20260605-phase0-overlay-sanity.md`, and matching ignored `outputs/phase0/mlxp/...` API artifacts.
- Artifact/checkpoint storage path: Phase 0 generated artifacts live under ignored repo-local `outputs/phase0/...`; no checkpoints were produced in Phase 0.
- Feature cache storage path: deferred until Phase 1/0.5 feature-cache implementation; no Phase 0 feature cache.
- WandB/logging policy: W&B was not used for deterministic Phase 0 data/evaluator smokes; future non-trivial training/evaluation runs should use entity `pjh6029-seoul-national-university` and project `fdm-1-with-d2e`.
