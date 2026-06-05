# Phase 0 MLXP preflight — real-D2E evidence

Date: 2026-06-05  
Ultragoal story: G008 — operational preflight for real-D2E MLXP smoke  
Operational source: `docs/reproduction_spec/OPERATIONAL_RULES.md`  
MLXP source: repo `AGENTS.md` + `mlxp-reservation-api` workflow

## Status

Preflight is complete for the bounded real-D2E Phase 0 smoke. The next story (G009) may reserve a production MLXP pod using the smallest practical allocation and must cancel it when idle. Routine MLXP reservations/cancellations for this project are pre-authorized by the repo operational rules.

## Code and image

- Branch: `codex/phase-0`
- Pushed code SHA for cluster checkout: `19f72208c19efab5d8b507b6e14447f8e06f1883`
- Pushed remote: `origin/codex/phase-0`
- Dockerfile: `docker/phase0.Dockerfile`
- Image tag: `docker.io/pjh6029/fdm-1-with-d2e:phase0-20260605-19f7220`
- Image ref with digest: `docker.io/pjh6029/fdm-1-with-d2e:phase0-20260605-19f7220@sha256:e9b17d5c46110538338c0473b059b637facdcdc196438f67e9c378c3ff8e0235`
- Docker evidence logs:
  - `outputs/phase0/docker/20260605-19f7220/docker-build.log`
  - `outputs/phase0/docker/20260605-19f7220/docker-pytest.log` (`54 passed` inside container)
  - `outputs/phase0/docker/20260605-19f7220/docker-push.log`
  - `outputs/phase0/docker/20260605-19f7220/docker-imagetools.txt`

## Local verification before cluster

- `uv run --locked pytest` → `54 passed` (recorded in `outputs/phase0/local-evidence/20260605-g007/pytest.log`).
- `uv run --locked python -m compileall src scripts tests` → passed.
- Container full verification: `docker run --rm docker.io/pjh6029/fdm-1-with-d2e:phase0-20260605-19f7220 uv run --locked pytest -q` → `54 passed`.

## Cluster constraints confirmed

- Project/member: production / normal member flow.
- Do not use MLXP debug project/namespace.
- Production reservation must stay within one node.
- Use the custom public Docker Hub image above; do not use `latest`.
- Use `uv` for Python commands inside the cluster clone.
- Cluster clone path: `/mnt/ddn/prod-runs/jeonghunpark/code/continuous-gui-poc/fdm-1-with-d2e`.
- D2E dataset path: `/mnt/ddn/extra-ddn-continuous-gui/`.
- Treat the dataset path as read-only. Do not write outputs, temp files, reports, caches, checkpoints, or pseudo-labels into it; do not use `.source-metadata/` as training input.
- Store generated smoke artifacts under the PVC repo clone, outside the dataset tree: `/mnt/ddn/prod-runs/jeonghunpark/code/continuous-gui-poc/fdm-1-with-d2e/outputs/phase0/real-d2e-smoke/20260605-g009/`.
- W&B is not required for this bounded data/evaluator smoke because it is not non-trivial training/evaluation; if later promoted to non-trivial evaluation, use entity `pjh6029-seoul-national-university` and project `fdm-1-with-d2e`.
- Cancel the MLXP pod immediately after artifacts/logs are saved or if the job fails early and the next expected work is local debugging.

## Reservation plan for G009

Use the `mlxp-reservation-api` workflow. Before creating a reservation, fetch the production board and read valid image/registry fields. Use a custom image reservation with:

- `image_path`: `docker.io/pjh6029/fdm-1-with-d2e:phase0-20260605-19f7220@sha256:e9b17d5c46110538338c0473b059b637facdcdc196438f67e9c378c3ff8e0235`
- `command`: `["sleep"]`
- `args`: `["infinity"]`
- `purpose` prefix: `fdm-1-with-d2e phase0 real-D2E smoke`
- GPU count: smallest available/practical allocation, expected `1` if the board requires GPU-backed pods.

Do not invent `managed_image_key` or `registry_profile_key`; leave registry profile empty for public Docker Hub unless the board exposes a matching Docker Hub profile.

## Planned cluster commands for G009

Inside the reservation, run from the cluster clone path:

```bash
cd /mnt/ddn/prod-runs/jeonghunpark/code/continuous-gui-poc/fdm-1-with-d2e
git fetch origin codex/phase-0
git checkout 19f72208c19efab5d8b507b6e14447f8e06f1883
mkdir -p outputs/phase0/real-d2e-smoke/20260605-g009/{logs,artifacts}
uv run --locked pytest tests/smoke tests/unit/data tests/unit/evaluation
uv run --locked python scripts/build_d2e_manifest.py \
  --dataset-root /mnt/ddn/extra-ddn-continuous-gui \
  --output outputs/phase0/real-d2e-smoke/20260605-g009/artifacts/dataset_manifest.json \
  --split-output outputs/phase0/real-d2e-smoke/20260605-g009/artifacts/split_manifest.json \
  --scale-output outputs/phase0/real-d2e-smoke/20260605-g009/artifacts/scale_manifest.json \
  --optional-scale 5 \
  --json > outputs/phase0/real-d2e-smoke/20260605-g009/artifacts/build_d2e_manifest.stdout.json
uv run --locked python scripts/locate_d2e_reference.py --json \
  > outputs/phase0/real-d2e-smoke/20260605-g009/artifacts/d2e_reference.json
```

After dataset discovery, add the smallest feasible reader/timestamp/evaluator smoke. If exact real MCAP decoding or official `evaluate.py` invocation is blocked by optional dependency/schema issues, write a deviation table and failure note under `notes/runs/` or `notes/failures/`, then cancel the pod and continue locally.

## Known preflight risks

- The current package has an optional OWAMcap adapter, but real OWAMcap schema compatibility is intentionally not proven until G009.
- The Phase 0 image is CPU/offline focused. If real MCAP decoding needs additional `mcap-owa-support`/`owa-msgs` packages, G009 should record the exact dependency blocker and either run via `uv run --with ...` or add a follow-up implementation/image story.
- Official D2E `evaluate.py` invocation is still a required follow-up for phase exit when practical.
