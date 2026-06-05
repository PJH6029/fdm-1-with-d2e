# Phase 0 local evidence run — fixture/offline foundation

Date: 2026-06-05  
Ultragoal story: `G007-run-local-phase-0-verification-and-e`  
Phase plan: `notes/plans/phase-0-data/20260605-data-foundation-plan.md`  
Branch: `codex/phase-0`  
Git HEAD before commit/push: `e3bb9534edf01bc7c9d687809b29fcbc543c3048`  
Working tree: dirty with Phase 0 implementation files; MLXP work must use a later committed/pushed SHA.

## Scope

Local-only, offline Phase 0 verification for stories G001–G006. This run validates package bootstrap, reader/binning, tokenizer/de-tokenizer, manifest/distribution builders, local evaluator/reference records, floor/probe scaffolds, and the non-final FDM-1 target-gap rubric draft.

No MLXP, GPU, Hugging Face download, live network, real D2E dataset, W&B, or MCAP official evaluator invocation was used in this run.

## Commands and evidence

Artifacts and logs are under:

```text
outputs/phase0/local-evidence/20260605-g007/
  logs/context.txt
  logs/pytest-all.txt
  logs/compileall.txt
  artifacts/dataset_manifest.json
  artifacts/split_manifest.json
  artifacts/scale_manifest.json
  artifacts/action_distribution.json
  artifacts/d2e_roundtrip_check.json
  artifacts/d2e_reference.json
  artifacts/artifact_summary.json
```

Executed commands:

```bash
uv run --locked pytest
uv run --locked python -m compileall -q src scripts tests
uv run --locked python scripts/build_d2e_manifest.py \
  --dataset-root outputs/phase0/local-evidence/20260605-g007/synthetic_d2e \
  --duration-metadata outputs/phase0/local-evidence/20260605-g007/artifacts/durations.json \
  --output outputs/phase0/local-evidence/20260605-g007/artifacts/dataset_manifest.json \
  --split-output outputs/phase0/local-evidence/20260605-g007/artifacts/split_manifest.json \
  --scale-output outputs/phase0/local-evidence/20260605-g007/artifacts/scale_manifest.json \
  --held-out-game game_beta \
  --optional-scale 5 \
  --json
uv run --locked python scripts/summarize_action_distribution.py \
  --dataset-manifest outputs/phase0/local-evidence/20260605-g007/artifacts/dataset_manifest.json \
  --bins-json outputs/phase0/local-evidence/20260605-g007/artifacts/bins.json \
  --output outputs/phase0/local-evidence/20260605-g007/artifacts/action_distribution.json \
  --json
uv run --locked python scripts/d2e_roundtrip_check.py --json
uv run --locked python scripts/locate_d2e_reference.py --json
```

Verification result:

- `uv run --locked pytest` → `54 passed`.
- `uv run --locked python -m compileall -q src scripts tests` → passed.
- `d2e_roundtrip_check.py --json` → `fixture_roundtrip_passed` with all six local D2E-style metric values equal to `1.0`.
- `locate_d2e_reference.py --json` → official reference record available for upstream D2E commit `80e98e26e4dc584ec76fec5789b4a97c275dd032`, model `open-world-agents/Generalist-IDM-1B`, dataset `open-world-agents/D2E-480p`.

## Fixture manifest evidence

Synthetic manifest artifacts exercise package/CLI paths only. They are not real D2E evidence.

- Dataset manifest: `phase0-dataset-3213c6c601dd815f`; 3 recordings, 2 games.
- Split manifest: `phase0-split-ce8f1bcfb60bdfdd`; held-out game `game_beta`, train 1, validation 0, test 1, held-out-test 1.
- Scale manifest: `phase0-scale-550b4c38728f8388`; scales `5/10/50/100%` over the synthetic training split.
- Action distribution: `phase0-action-distribution-2c55d14b2f56e6ce`; 7 bins, no-op rate `0.428571428571`, overflow rate `0.0`, raw mouse summaries by game and total.

## Known limitations / follow-up

- This is local fixture evidence only. It does not prove real OWAMcap schema compatibility, real D2E timestamp alignment, or full dataset action distributions.
- Official D2E `evaluate.py` was not invoked; `configs/data/d2e_reference.json` records the deviation and follow-up requirement for the MLXP/real-MCAP smoke.
- Working tree must be committed and pushed before G008/G009 MLXP work.
- Do not update `ROADMAP.md` or `DECISIONS.md` from this run alone beyond local scaffold evidence; final Phase 0 status needs real-D2E/MLXP and phase-exit GPT-Pro evidence.
