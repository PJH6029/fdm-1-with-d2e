# FDM-1 with D2E repo instructions

This repository is for a serious D2E-based reproduction of the public FDM-1 training recipe, not a smoke-test PoC. The research target is to build and evaluate a reproducible Video Encoder → IDM → pseudo-labeling → FDM pipeline on real D2E data, with trained checkpoints, ablations/scaling curves, failure analysis, and stable desktop/game or replay-control harness behavior.

## Research source of truth

- Primary reproduction spec: `docs/reproduction_spec/CANONICAL_SPEC.md`.
- Operational rules: `docs/reproduction_spec/OPERATIONAL_RULES.md`.
- Progress tracker: `docs/reproduction_spec/ROADMAP.md`.
- Decision register: `docs/reproduction_spec/DECISIONS.md`.
- Component/protocol details: `docs/reproduction_spec/spec/`.
- Literature survey: `docs/literature_survey/`.

For normal reproduction execution, treat every file under `docs/reproduction_spec/` as read-only except:

- `docs/reproduction_spec/ROADMAP.md` for checklist/status updates;
- `docs/reproduction_spec/DECISIONS.md` for finalized research/operational choices.

Do not use `AGENTS.md`, `CANONICAL_SPEC.md`, `OPERATIONAL_RULES.md`, or component specs as work logs. Edit specs only when the user explicitly asks for a spec revision.

At the end of every substantive task, review `ROADMAP.md` and `DECISIONS.md`. If the work completes checklist items, changes status, or resolves an open choice, update the relevant checkboxes/decision slots.

## Repository structure

Current reproduction intent comes from `docs/reproduction_spec/`.

Preferred structure for this repo:

```text
fdm-1-with-d2e/
  docs/
    literature_survey/
    reproduction_spec/

  src/
    fdm_1_with_d2e/
      data/             # D2E/MCAP reading, manifests, splits, 50ms binning
      tokenization/     # action vocab, mouse bins, de-tokenization
      video/            # encoders, feature cache, resamplers, probes, adaptation
      models/           # VE/IDM/FDM modules, diffusion components, heads
      training/         # train loops, losses, distributed/checkpoint utilities
      pseudo_labeling/  # IDM inference, confidence filtering, pseudo-label datasets
      evaluation/       # D2E metrics, aggregation, free-running, target-gap, scaling
      harness/          # replay-control/desktop harness adapters and safety
      cluster/          # MLXP/run records/W&B utilities
      reporting/        # tables, plots, report assets, failure analysis

  configs/
    data/
    tokenization/
    video_encoder/
    idm/
    fdm/
    pseudo_labeling/
    evaluation/
    harness/
    cluster/
    experiments/

  schemas/
  scripts/
  tests/
  docker/
  notes/
    runs/
    experiments/
    investigations/
    failures/

  outputs/        # generated, ignored
  runs/           # generated, ignored
  checkpoints/    # generated, ignored
  feature_cache/  # generated, ignored
```

Structure rules:

- Put reusable implementation code in `src/fdm_1_with_d2e/`.
- Keep `scripts/` as thin CLI wrappers over package code; avoid large one-off scripts.
- Commit reproducible configs under `configs/`; put run-specific experiment configs under `configs/experiments/<phase-or-date>/` when needed.
- Commit JSON schemas for manifests, metrics, run records, pseudo labels, action vocab, and checkpoint metadata under `schemas/`.
- Split tests into `tests/unit/`, `tests/integration/`, and `tests/smoke/` as coverage grows.
- Treat `outputs/`, `runs/`, `checkpoints/`, and `feature_cache/` as generated artifact directories; do not commit their contents unless a tiny fixture is explicitly required for tests.
- `../fdm-d2e-reproduction` is stale old attempt. Do not use the old repo work. Its old objective/metrics/spec are not authoritative for this repo; Avoid copying the old repo's run-specific script/config sprawl. Generalize useful patterns into package modules, configs, and notes.


## Operational rules for this repo

- Edit code/docs locally in this repository.
- GPU training, large feature extraction, pseudo-label generation, full evaluation, and dataset-dependent runs must execute on the MLXP cluster.
- Default workflow:
  1. local edit and small local checks;
  2. commit and push;
  3. reserve an MLXP pod when cluster/GPU/data access is needed;
  4. in the cluster clone, pull the pushed commit;
  5. run the job from the recorded git SHA/config/image;
  6. preserve metrics/checkpoints/run records;
  7. cancel the reservation when GPU work will be idle.
- Cluster clone/PVC repo path:
  `/mnt/ddn/prod-runs/jeonghunpark/code/continuous-gui-poc/fdm-1-with-d2e`.
- D2E dataset path in MLXP pods:
  `/mnt/ddn/extra-ddn-continuous-gui/`.
- Treat the dataset path as read-only. Never write checkpoints, caches, pseudo-labels, reports, or temp files into the dataset tree. Do not use `.source-metadata/` as training input.
- Use `MLXP.md` and `docs/reproduction_spec/OPERATIONAL_RULES.md` for reservation payload details. `MLXP_ACCESS_TOKEN` is in `.env`; never commit secrets.
- Routine MLXP reservations/cancellations within this project are pre-authorized. Use the `mlxp-reservation-api` workflow when reserving, inspecting, or cancelling pods.
- Use custom public Docker Hub images for cluster jobs, default repo `docker.io/pjh6029/fdm-1-with-d2e`. Prefer immutable tags like `<role>-<yyyymmdd>-<gitsha>` and record image digest; do not use `latest` for training/evaluation jobs.
- Reserve the smallest GPU count that keeps the job efficient. Use 1 GPU for smoke/data/Tiny checks and 2–4 H200 GPUs only when the path is multi-GPU ready. Cancel pods when the next expected work is local coding, docs, or long non-GPU inspection.
- Use W&B for non-trivial training/evaluation logs with entity `pjh6029-seoul-national-university` and project `fdm-1-with-d2e`; keep `WANDB_API_KEY` in `.env` only.

## Work notes and run records

Write working notes, experiment summaries, run records, debugging notes, and failure analyses under `notes/`, not in `AGENTS.md` or `docs/reproduction_spec/`.

Use subdirectories rather than loose markdown files directly under `notes/`:

- `notes/runs/` — MLXP run records, command/config/checkpoint/metric pointers, W&B links, reservation IDs.
- `notes/experiments/` — ablation/scaling summaries, interpretation, tables copied from metrics, comparison notes.
- `notes/investigations/` — debugging, data inspection, implementation research, root-cause analysis.
- `notes/failures/` — failed runs, negative results, harness failures, reproduction gaps that should inform the final report.

Recommended filename format: `YYYYMMDD-<stage>-<short-topic>.md`, for example `notes/runs/20260604-idm-tiny-mdlm16.md`.

Notes may contain intermediate observations, but finalized decisions must also be reflected in `docs/reproduction_spec/DECISIONS.md`, and completed/blocked roadmap items must be reflected in `docs/reproduction_spec/ROADMAP.md`.

## Completion discipline

Before claiming a task is complete, verify the relevant code/docs/tests or explain why verification could not run. For reproduction work, completion normally requires:

- local changes committed and pushed before cluster execution;
- cluster runs tied to a git SHA, image tag/digest, config, dataset/split manifest, and W&B/run record when applicable;
- artifacts stored outside the dataset tree;
- `ROADMAP.md` and `DECISIONS.md` reviewed and updated if needed;
- notes written under the appropriate `notes/<category>/` directory for any substantive run, experiment, investigation, or failure.
