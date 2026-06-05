# Operational Rules for FDM-1 with D2E

These rules govern execution logistics. Research choices belong in `CANONICAL_SPEC.md`; this file is about where and how work runs.

## 1. Local vs MLXP execution

- Code and documentation are edited in the local repository.
- GPU training, large feature extraction, pseudo-label generation, and full evaluation must run on the MLXP cluster.
- The corresponding cluster clone is:

```text
/mnt/ddn/prod-runs/jeonghunpark/code/continuous-gui-poc/fdm-1-with-d2e
```

Default workflow:

```text
local edit/test small checks
  → git commit/push
  → reserve MLXP pod when GPU/cluster data is needed
  → pull in /mnt/ddn/prod-runs/jeonghunpark/code/continuous-gui-poc/fdm-1-with-d2e
  → run job with recorded git SHA/config/image
  → copy metrics/checkpoints to persistent artifact paths
  → cancel reservation when GPU will be idle
```

Do not make cluster-only code changes without back-porting them to the local repo and pushing them.

## 2. MLXP reservation policy

Use the `mlxp-reservation-api` workflow and `MLXP.md` for API/controller details. The paths in this file are canonical for this reproduction repo.

Known project facts for this repo:

- project: `production`
- member: `jeonghunpark`
- API token: local `.env` key `MLXP_ACCESS_TOKEN` (never commit it)
- purpose prefix: `Continuous GUI - FDM reproduction`
- quota: up to `4x H200`
- storage/PVC repo path: `/mnt/ddn/prod-runs/jeonghunpark/code/continuous-gui-poc/fdm-1-with-d2e`
- image source: custom Docker image from Docker Hub, default repository `docker.io/pjh6029/fdm-1-with-d2e`

Project-specific authorization: routine GPU reservations and cancellations for this project are pre-authorized by the user. Agents may schedule/cancel reservations without additional conversational confirmation when the reservation stays within the constraints above. Still log the exact JSON payload before creation, use only owner/member endpoints, and never use admin override endpoints.

Ask the user before any materially broader external action, including: more than 4 GPUs, quota-increase requests, new credentials, non-project images, admin routes, destructive data/artifact deletion, or reservations unrelated to this project.

## 3. Reservation payload rules

- Fetch the board before creating a reservation.
- Do not invent `managed_image_key` or `registry_profile_key`; read valid values from the board payload.
- Use exactly one of `managed_image_key` or `image_path`.
- Custom image reservations require `image_path`; set `command` and `args` only with `image_path`.
- For public Docker Hub images, set `image_path` to the full `docker.io/pjh6029/...:<tag>` reference and leave `registry_profile_key` empty unless the board exposes a matching Docker Hub registry profile.
- Production reservations must stay within one node.
- Do not use `debug` project/namespace. dataset path `/mnt/ddn/extra-ddn-continuous-gui/` is stale in the debug namespace.

> Tip: To create a reservation immediately for empty slots, you can start from a cell that includes the current time. (e.g., if currently 15:36, reserve from 15:00)

## 4. Container/image policy

- Cluster jobs must use a custom image from Docker Hub.
- Use one canonical Docker Hub repository by default: `docker.io/pjh6029/fdm-1-with-d2e`.
- Manage project variants as tags, not separate repositories, unless an image has a distinct lifecycle, permission boundary, or runtime contract.
- Recommended tag format: `<role>-<yyyymmdd>-<gitsha>`, e.g. `train-20260604-53d524c`, `eval-20260604-53d524c`, `probe-20260604-53d524c`.
- Do not use floating tags such as `latest` in MLXP training/evaluation payloads; record immutable tag plus digest in every run directory.
- The image must be public so that it can be pullable by the MLXP cluster.
- If dependencies change, rebuild/push the image before reserving expensive GPU time.
- For shell/probe pods, use a non-exiting command such as `command: ["sleep"]`, `args: ["infinity"]`; for training pods, record the explicit launcher command in the run record.

## 5. GPU utilization policy

- Reserve the smallest GPU count that keeps the job efficient.
- Use 1 GPU for smoke/data checks and Tiny-model debugging.
- Use 2–4 H200 GPUs for sustained Base-model training, large feature extraction, and pseudo-label generation when the code path is multi-GPU ready.
- Consider DDP/FSDP/DeepSpeed or equivalent multi-GPU parallelism before requesting multiple GPUs.
- Cancel reservations when the next expected work is local coding, documentation, log inspection, or any non-GPU task likely to exceed about 30 minutes.
- If a job fails early or GPU utilization is persistently low, cancel, debug locally or on cheaper resources, then re-reserve.

## 6. Dataset and artifact storage

Persistent repo path in MLXP pods:

```text
/mnt/ddn/prod-runs/jeonghunpark/code/continuous-gui-poc/fdm-1-with-d2e
```

Input dataset path in MLXP pods:

```text
/mnt/ddn/extra-ddn-continuous-gui/
    labeled/
        README.md
        <game-name>/
            <recording>.mkv
            <recording>.mcap
        .source-metadata/        # provenance and verification artifacts, not training input
    unlabeled/
        README.md
        <game-name>/
            <video>.mkv
        .source-metadata/        # provenance and verification artifacts, not training input
```

Rules:

- Treat the dataset directory as read-only.
- Do not write checkpoints, caches, generated pseudo-labels, reports, or temporary files into the dataset tree.
- Do not use `.source-metadata/` as model training input; it is provenance/verification metadata only.
- Store run artifacts outside the dataset tree, preferably under ignored repo-local/persistent paths such as `outputs/`, `runs/`, `checkpoints/`, or a project artifact directory on the PVC.
- Use NVMe only for volatile scratch/cache; copy durable metrics/checkpoints back to persistent storage before releasing the pod.

## 7. Experiment tracking

Use Weights & Biases for training logs, evaluation curves, ablations, and scaling runs.

- Configure W&B via `.env`; never commit `WANDB_API_KEY`.
- Canonical W&B target:

```text
WANDB_ENTITY=pjh6029-seoul-national-university
WANDB_PROJECT=fdm-1-with-d2e
```

- Every non-trivial training/evaluation job should create a W&B run unless the cluster/network is unavailable.
- W&B run names should include stage/model, scale or split, date, and git SHA, e.g. `idm-base-labeled100-20260604-53d524c`.
- W&B tags/config should include model family (`ve`, `idm`, `fdm`), dataset split/scale, game subset, git SHA, image tag/digest, MLXP reservation ID, and config path.
- If online logging fails, run with offline/local logs and sync later; do not block checkpoint preservation on W&B availability.

## 8. Required run record

Every non-trivial cluster run must write a run record containing:

- git SHA and branch;
- container image tag/digest;
- MLXP reservation ID, project, node, GPU indices/count, start/end times;
- W&B entity/project and run ID or URL when used;
- dataset manifest ID and split/scale manifest;
- config file path and resolved config JSON/YAML;
- command line and environment summary;
- checkpoint paths;
- metrics JSON paths;
- failure notes or resume instructions.

## 9. Reproducibility and reporting

- Prefer config-driven commands over ad-hoc shell flags.
- All final metrics must be reproducible from committed code, committed configs, and recorded dataset manifests.
- Checkpoints used in the final report must be immutable or content-addressed.
- Reports must include failed runs and negative results when they affect design decisions.
