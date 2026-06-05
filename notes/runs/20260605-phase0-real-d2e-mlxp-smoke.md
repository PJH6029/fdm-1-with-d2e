# Phase 0 real-D2E MLXP smoke — manifests, action distribution, evaluator

Date: 2026-06-05 / 2026-06-06 KST  
Ultragoal story: G009 — bounded real-D2E manifest, reader, and evaluator smoke  
Code SHA: `f801bce287bafbd8ea8b1d2e225dcd707a8fba72`  
Branch: `codex/phase-0`  
Image: `docker.io/pjh6029/fdm-1-with-d2e:phase0-20260605-f801bce@sha256:4a78401935fa9660aab5f17ea5872dfc21a1f67cba0df269a4ac50ae287d2ae1`

## Reservation lifecycle

- Exploratory reservation: `rsv-jeonghunpark-20260606-d3f8d2`, production namespace `p-production`, one H200 GPU on node 5, image `phase0-20260605-19f7220@sha256:e9b17d5c46110538338c0473b059b637facdcdc196438f67e9c378c3ff8e0235`; cancelled after it exposed the need for committed JSON MCAP decoder support.
- Final reservation: `rsv-jeonghunpark-20260606-525828`, production namespace `p-production`, one H200 GPU on node 5, image above; cancelled after artifact capture.
- No MLXP debug namespace/project used.
- Dataset path: `/mnt/ddn/extra-ddn-continuous-gui/` treated as read-only by policy. The pod user reported filesystem write permission, so the run deliberately wrote all outputs under the repo clone instead of the dataset tree.
- Artifact root copied locally from PVC: `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/`.

## Verification commands and results

- Local before cluster: `uv run --locked pytest` → `57 passed`; compileall and `git diff --check` passed.
- Container verification before push: `docker run --rm phase0-20260605-f801bce uv run --locked pytest -q` → `57 passed`.
- Cluster checkout: `git checkout f801bce287bafbd8ea8b1d2e225dcd707a8fba72`.
- Cluster tests: `uv run --locked pytest tests/smoke tests/unit/data tests/unit/evaluation tests/integration/data` → `31 passed`.
- Real manifest build: `uv run --locked python scripts/build_d2e_manifest.py --dataset-root /mnt/ddn/extra-ddn-continuous-gui ...`.
- Real action distribution: `uv run --with mcap python scripts/summarize_action_distribution.py --from-mcap-json --one-per-game ...`.
- Local evaluator fixture smoke: `uv run --locked python scripts/d2e_roundtrip_check.py --json`.
- Official evaluator smoke: pinned `worv-ai/D2E` commit `80e98e26e4dc584ec76fec5789b4a97c275dd032`; same-MCAP Apex ground truth/prediction with `uv run evaluate.py`.

## Artifacts

- Manifest stdout: `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/artifacts/build_d2e_manifest.stdout.json`
- Dataset manifest: `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/artifacts/dataset_manifest.json`
- Split manifest: `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/artifacts/split_manifest.json`
- Scale manifest: `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/artifacts/scale_manifest.json`
- Real action distribution: `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/artifacts/action_distribution_one_per_game_from_committed_cli.json`
- Local round-trip check: `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/artifacts/d2e_roundtrip_check.json`
- Official D2E reference: `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/artifacts/d2e_reference.json`
- Official `evaluate.py` source excerpt: `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/artifacts/official_evaluate_py_head.txt`
- Official same-MCAP metrics: `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/artifacts/official_evaluate_same_mcap_apex.json`
- Official same-MCAP status/deviation: `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/artifacts/official_evaluate_same_mcap_apex_status.json`
- Reservation/API evidence: `outputs/phase0/mlxp/20260605-g009-f801bce/`
- Docker evidence: `outputs/phase0/docker/20260605-f801bce/`

## Evidence summary

- Real labeled D2E discovery found `459` `.mkv`/`.mcap` pairs across `29` games under `labeled/`, excluding `.source-metadata/`.
- Split manifest counts: train `367`, validation `46`, test `46`, held-out test `0`. Underfilled games recorded by split builder: `OguForest`, `Skul`, `VALORANT`.
- Scale manifest percentages/counts: `5% = 36`, `10% = 50`, `50% = 193`, `100% = 367` train recordings.
- Committed real-MCAP JSON action distribution ran one recording per game: `29` recordings, `29` games, `1,832,113` bins, `1,161,652` events, no-op rate `0.516233987751`, overflow rate `0.0`, source `mcap_json`.
- Local evaluator fixture round-trip passed with all six local metric values `1.0` and `9` writer-compatible records.
- Official same-MCAP Apex evaluation passed after runtime library recovery. Metrics: `29,242` bins, duration `1462.052619` s, mouse Pearson X `1.0`, mouse Pearson Y `0.9999999999999998`, mouse scale X/Y `1.0`, mouse button accuracy `1.0`, keyboard key accuracy `1.0`.

## Deviations and follow-ups

- The Phase 0 Docker image is sufficient for committed data/manifest/action-distribution tests, but pinned official D2E `evaluate.py` needed Debian runtime GUI libraries (`libxcb1 libx11-6 libgl1 libglib2.0-0`) installed inside the pod before the same-MCAP evaluator smoke passed. A future official-evaluation image should bake these libraries instead of relying on pod-local `apt-get`.
- Real action distribution uses raw `mouse/raw` `last_x,last_y` for relative motion; absolute `mouse` move events are counted diagnostically and ignored for action deltas by policy.
- Keyboard labels are stable `VK_<int>` pending later key-name policy audit.
- The official same-MCAP smoke verifies evaluator path compatibility and GT round-trip sanity, not model prediction quality.
- W&B was not used because this was bounded data/evaluator smoke, not non-trivial training/evaluation.
