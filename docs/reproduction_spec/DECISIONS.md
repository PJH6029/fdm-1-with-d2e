# Reproduction Decisions Register

Canonical source: `./CANONICAL_SPEC.md`. Record final decisions here as they are made. Do not leave major decisions implicit in code.

## Data decisions

- D2E dataset revision / local manifest ID:
- Exact game list and categories:
- Train/val/test split policy:
- Held-out-game split:
- Scale subset construction:
- Menu/loading/inactive segment policy:
- Audio policy: out of first canonical scope unless promoted.
- Active window metadata policy:

## Tokenization decisions

- Timebase: `50ms` bins.
- Sparse event slots: default `K=8`.
- Mouse tokenization: default 49x49 compound signed exponential bins.
- Mouse bin fitting data:
- Scroll representation:
- Click-position auxiliary grid/horizon:
- Key/button state auxiliary targets:
- Overflow threshold/action:

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

- D2E-Generalist-IDM-1B reference checkpoint/revision:
- Generalist-IDM inference command/path:
- Generalist-IDM evaluation compatibility notes:
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

- FDM-1 target-gap rubric:
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

- Primary aggregate metric/composite:
- Bootstrap/repeated-seed protocol:
- Harness type and scenarios:
- Reported failure categories:
- Criteria for promoting optional ablations:

## Operational decisions

- Docker image tag/digest:
- MLXP reservation/run record location:
- Artifact/checkpoint storage path:
- Feature cache storage path:
- WandB/TensorBoard/logging policy:
