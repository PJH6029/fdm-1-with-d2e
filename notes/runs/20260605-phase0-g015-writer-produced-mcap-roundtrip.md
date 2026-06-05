# Phase 0 G015 — writer-produced MCAP official round-trip

Date: 2026-06-05 / 2026-06-06 KST  
Ultragoal story: `G015-run-writer-produced-mcap-official-roundtrip`  
Purpose: close the Phase 0 exit-review blocker that required pinned official D2E `evaluate.py` to score a repo-generated prediction MCAP rather than a copied ground-truth MCAP.

## Code and image

- Branch: `codex/phase-0`
- Git SHA used on MLXP: `ee08fb847b24d514db230e1d17f8f2400b3cbe10`
- Relevant commits:
  - `fbe32e7` — optional OWA writer adapter with `exact` and `tokenized` action modes.
  - `ee08fb8` — Phase 0 Docker image includes official-evaluator runtime libraries (`libgl1`, `libglib2.0-0`, `libx11-6`, `libxcb1`).
- Docker image: `docker.io/pjh6029/fdm-1-with-d2e:phase0-20260605-ee08fb8@sha256:4b6d2e78f8f6393ca0e8b23af21de50fc852c292cdd2c934cb2a05f31d6555cb`
- Image build verification:
  - Docker build smoke: `5 passed` inside image (`tests/smoke` + bootstrap configs).
  - Docker run full suite: `62 passed`.

## Reservation and cluster environment

- Reservation: `rsv-jeonghunpark-20260606-e183b7`
- Project/namespace: `production` / `p-production`
- Node/GPU: node `5`, GPU index `[0]`, one H200.
- Time window: `2026-06-06T01:00:00+09:00` to `2026-06-06T04:00:00+09:00`.
- Status: cancelled after artifact copy (`reservation-cancel.json`, `reservation-detail-after-cancel.json`).
- Cluster repo path: `/mnt/ddn/prod-runs/jeonghunpark/code/continuous-gui-poc/fdm-1-with-d2e`
- Dataset root: `/mnt/ddn/extra-ddn-continuous-gui`
  - Pod reported the dataset root as writable, but the run treated it as policy-read-only; all generated files were written under repo-local `outputs/`.
- W&B: not used; this was a deterministic data/evaluator smoke, not training or non-trivial model evaluation.

## Inputs and pinned references

- Source recording: `/mnt/ddn/extra-ddn-continuous-gui/labeled/Apex_Legends/0805_01.mcap`
- Source SHA256: `da003e63e09f4a019e9411ca4bb39f5a494ffdfab71c39bb3339076a63642246`
- Source size: `13,723,487` bytes.
- Official D2E repo path on cluster: `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/official_d2e_repo`
- Official D2E commit: `80e98e26e4dc584ec76fec5789b4a97c275dd032`
- Official evaluator: pinned `evaluate.py`, 50ms bins, first-screen PTS alignment.
- Optional OWA dependency source smoke recorded in `owa-dependency-smoke.json`.

## Commands

The cluster script is copied locally at:

- `outputs/phase0/mlxp/20260605-g015-writer-roundtrip/run-g015-writer-roundtrip.sh`

High-level command sequence:

```bash
git fetch origin codex/phase-0
git checkout codex/phase-0
git pull --ff-only origin codex/phase-0
uv run --locked pytest tests/smoke tests/unit/evaluation/test_official_roundtrip.py tests/integration/evaluation/test_d2e_roundtrip_and_cli.py -q
uv run --locked python -m compileall src scripts tests

for MODE in exact tokenized; do
  uv run \
    --with 'mcap-owa-support @ git+https://github.com/lastdefiance20/open-world-agents.git#subdirectory=projects/mcap-owa-support' \
    --with 'owa-core @ git+https://github.com/lastdefiance20/open-world-agents.git#subdirectory=projects/owa-core' \
    --with 'owa-msgs @ git+https://github.com/lastdefiance20/open-world-agents.git#subdirectory=projects/owa-msgs' \
    python scripts/d2e_generate_roundtrip_prediction_mcap.py \
      --source-mcap /mnt/ddn/extra-ddn-continuous-gui/labeled/Apex_Legends/0805_01.mcap \
      --prediction-mcap outputs/phase0/g015-writer-roundtrip/20260605-g015-ee08fb8/apex_0805_01.${MODE}.prediction.mcap \
      --provenance-json outputs/phase0/g015-writer-roundtrip/20260605-g015-ee08fb8/apex_0805_01.${MODE}.prediction.mcap.provenance.json \
      --dataset-root /mnt/ddn/extra-ddn-continuous-gui \
      --action-mode "$MODE" \
      --overwrite \
      --json

  cd outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/official_d2e_repo
  env -u UV_PROJECT_ENVIRONMENT uv run evaluate.py \
    /mnt/ddn/extra-ddn-continuous-gui/labeled/Apex_Legends/0805_01.mcap \
    /mnt/ddn/prod-runs/jeonghunpark/code/continuous-gui-poc/fdm-1-with-d2e/outputs/phase0/g015-writer-roundtrip/20260605-g015-ee08fb8/apex_0805_01.${MODE}.prediction.mcap \
    --output /mnt/ddn/prod-runs/jeonghunpark/code/continuous-gui-poc/fdm-1-with-d2e/outputs/phase0/g015-writer-roundtrip/20260605-g015-ee08fb8/official_evaluate_${MODE}.json
done
```

## Artifacts

Local copied artifact directory:

- `outputs/phase0/g015-writer-roundtrip/20260605-g015-ee08fb8/`

Key files:

- `summary.json`
- `cluster-run.stdout.log`, `cluster-run.stderr.log`
- `pytest-targeted.stdout.log`, `compileall.stdout.log`
- `generate_exact.stdout.json`, `generate_tokenized.stdout.json`
- `apex_0805_01.exact.prediction.mcap`, `apex_0805_01.exact.prediction.mcap.provenance.json`
- `apex_0805_01.tokenized.prediction.mcap`, `apex_0805_01.tokenized.prediction.mcap.provenance.json`
- `official_evaluate_exact.json`, `official_evaluate_tokenized.json`
- `git-sha.txt`, `official-d2e-sha.txt`, `owa-dependency-smoke.json`

MLXP reservation/API artifacts:

- `outputs/phase0/mlxp/20260605-g015-writer-roundtrip/`

## Results

Both generated prediction MCAPs have SHA256 and size different from the source MCAP, with writer metadata recorded in provenance.

### Exact OWA writer re-emission mode

Purpose: prove the repo can produce an official-evaluator-readable MCAP through `OWAMcapWriter` without byte-copying the source.

- Prediction SHA256: `4ac0a3d1af2ed37da26c5af86dbe9bb1050bd340a088e6f3d9e3dbfcafdc4188`
- Prediction size: `5,746,658` bytes.
- Topics written: keyboard `8261`, mouse/raw `77071`, screen `75629`.
- Official duration/bins: `1462.052619` sec, `29242` bins.
- Official metrics:
  - mouse pearson_x: `1.0`
  - mouse pearson_y: `0.9999999999999998`
  - mouse scale_ratio_x: `1.0`
  - mouse scale_ratio_y: `1.0`
  - mouse_button accuracy: `1.0`
  - keyboard key_accuracy: `1.0`

### Tokenized repo decoder → 50ms binning → tokenizer → de-tokenizer → OWA writer mode

Purpose: prove the Phase 0 action tokenization path can produce an official-evaluator-readable prediction MCAP, with expected quantization loss.

- Prediction SHA256: `429f2377426d53d85b32329246d3e1dc6e959b54f450927720026c0f8602a8d3`
- Prediction size: `3,707,555` bytes.
- Tokenized bins: `29242`.
- Overflow bins: `0`.
- Skipped scroll events: `593` (pinned official `evaluate.py` does not score scroll).
- Topics written: keyboard `8261`, mouse/raw `16199`, screen `75629`.
- Official duration/bins: `1462.052619` sec, `29242` bins.
- Official metrics:
  - mouse pearson_x: `0.9952013519490897`
  - mouse pearson_y: `0.995708268743024`
  - mouse scale_ratio_x: `1.021408011414067`
  - mouse scale_ratio_y: `1.0273500070777737`
  - mouse_button accuracy: `0.9941002949852508`
  - keyboard key_accuracy: `1.0`

Interpretation: exact mode closes the official writer/schema compatibility blocker with perfect metrics and non-copy provenance. Tokenized mode closes the repo tokenizer/de-tokenizer writer-path blocker, with high but not perfect mouse metrics due to expected 49x49 mouse quantization and sparse 50ms aggregation; keyboard is exact and mouse buttons are near exact with no token overflow.

## Phase implications

- G015 exit-review blocker is resolved by concrete MLXP evidence.
- Phase 0 has an evaluator-compatible real-MCAP writer path for later pseudo-label/FDM pipeline checks.
- Later phases should not treat tokenized-mode mouse scores as a model-quality baseline; this is a deterministic tokenizer/writer sanity check with quantization loss.
- If future official-evaluator runs use slim images, keep GUI/runtime libraries baked into the Dockerfile rather than using pod-local apt installs.
