# Phase 0 exit evidence summary

Date: 2026-06-05 / 2026-06-06 KST  
Scope: Phase 0 only — data pipeline, evaluator, and sanity checks. This summary does not start or claim Phase 0.5 work.

## Final status

Phase 0 is evidence-complete for the roadmap scope after the final writer-produced MCAP official-evaluator blocker from GPT-Pro was resolved, final review blockers were fixed, and terminal ROADMAP/DECISIONS updates were made from concrete evidence.

Latest pushed branch at summary creation and final review-fix update: `codex/phase-0`

## Core evidence bundle

### Planning and gates

- Phase plan: `notes/plans/phase-0-data/20260605-data-foundation-plan.md`
- Research-architect review: `notes/plans/phase-0-data/reviews/20260605-research-architect-review-1.md`
- Research-critic review: `notes/plans/phase-0-data/reviews/20260605-research-critic-review-1.md` (`APPROVE`)
- Phase-exit GPT-Pro artifacts: `notes/investigations/gpt_pro/phase-0-data/20260605-phase-exit-review/`
- GPT-Pro conversation: `https://chatgpt.com/c/6a22ef07-d1f8-83a9-83d4-8268febde7d8`
- GPT-Pro blocker accepted and resolved: pinned official D2E `evaluate.py` scored writer-produced prediction MCAPs, not only a copied/same ground-truth MCAP.

### Local implementation and verification

- Package/config/schema/bootstrap: `pyproject.toml`, `uv.lock`, `configs/`, `schemas/`, `scripts/`, `src/fdm_1_with_d2e/`.
- Reader/binning/video sampler: `src/fdm_1_with_d2e/data/`.
- Tokenizer/de-tokenizer: `src/fdm_1_with_d2e/tokenization/`.
- Official/local evaluator and writer support: `src/fdm_1_with_d2e/evaluation/`, `scripts/d2e_generate_roundtrip_prediction_mcap.py`.
- Manifest/action distribution builders: `src/fdm_1_with_d2e/data/manifests.py`, manifest CLIs.
- Floor/probe/target-gap scaffolds: `src/fdm_1_with_d2e/models/floors.py`, `src/fdm_1_with_d2e/video/scaffold.py`, `src/fdm_1_with_d2e/reporting/target_gap.py`.
- Final local verification after terminal review fixes:
  - `uv run --locked pytest tests/unit/data/test_manifests.py::test_scale_manifest_optional_percentages_are_nested_by_game tests/unit/evaluation/test_official_reference.py::test_committed_reference_record_matches_default_builder -q` → `2 passed`
  - `uv run --locked pytest -q` → `64 passed`
  - `uv run --locked python -m compileall src scripts tests` → passed
  - `git diff --check` → passed

### Real D2E / MLXP evidence

Run records:

- `notes/runs/20260605-phase0-real-d2e-mlxp-smoke.md`
- `notes/runs/20260605-phase0-g015-writer-produced-mcap-roundtrip.md`
- `notes/runs/20260605-phase0-overlay-sanity.md`
- `notes/runs/20260605-phase0-final-review-fixes.md`

Key real-D2E artifacts:

- `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/`
- `outputs/phase0/g015-writer-roundtrip/20260605-g015-ee08fb8/`
- `outputs/phase0/overlay-sanity/20260605-g014-ee21a18/`
- Matching MLXP API/reservation artifacts under `outputs/phase0/mlxp/`.

Dataset/source evidence:

- Dataset root: `/mnt/ddn/extra-ddn-continuous-gui` (treated read-only in every run).
- Dataset manifest: `phase0-dataset-75ae762b7c5aed63`, 459 labeled `.mkv`/`.mcap` pairs, 29 games.
- Split manifest: `phase0-split-56832b5d5d8c31e6`, train `367`, validation `46`, test `46`, held-out `0`.
- Scale manifest: `phase0-scale-d32d102e3412cfbe`, regenerated from copied real-D2E dataset/split manifests after the final review nesting fix; 5%=36, 10%=50, 50%=193, 100%=367 train recordings with 5⊆10⊆50⊆100 proof in `notes/runs/20260605-phase0-final-review-fixes.md`.
- Action distribution: `phase0-action-distribution-1b2de09a5ae4dc24`, 29 one-per-game summaries, 1,832,113 bins, 1,161,652 events, no-op fraction `0.516233987751`, overflow `0.0`.

Official D2E evaluator evidence:

- Pinned D2E repo commit: `80e98e26e4dc584ec76fec5789b4a97c275dd032`.
- Public reference model located: `open-world-agents/Generalist-IDM-1B`; inference path located but actual model inference deferred to Phase 2.
- G009 same-MCAP official Apex evaluation passed after runtime-library recovery.
- G015 exact writer-produced MCAP official evaluation on Apex:
  - source SHA256: `da003e63e09f4a019e9411ca4bb39f5a494ffdfab71c39bb3339076a63642246`
  - prediction SHA256: `4ac0a3d1af2ed37da26c5af86dbe9bb1050bd340a088e6f3d9e3dbfcafdc4188`
  - not byte-copied; provenance records different hash/size and writer metadata.
  - official metrics: mouse Pearson X/Y `1.0` / `0.9999999999999998`, scale X/Y `1.0` / `1.0`, mouse-button accuracy `1.0`, keyboard accuracy `1.0`.
- G015 tokenized writer-produced MCAP official evaluation on Apex:
  - prediction SHA256: `429f2377426d53d85b32329246d3e1dc6e959b54f450927720026c0f8602a8d3`
  - tokenized bins `29242`, overflow bins `0`, skipped scroll events `593` because pinned official evaluator does not score scroll.
  - official metrics: mouse Pearson X/Y `0.9952013519490897` / `0.995708268743024`, scale X/Y `1.021408011414067` / `1.0273500070777737`, mouse-button accuracy `0.9941002949852508`, keyboard accuracy `1.0`.

Overlay sanity:

- Six real Apex `.mkv` frames with decoded keyboard/mouse/scroll overlays were generated outside the dataset tree.
- Two representative frames were inspected locally with `view_image` and looked plausible for active FPS/UI interaction.

### Operational evidence

- Final Phase 0 image: `docker.io/pjh6029/fdm-1-with-d2e:phase0-20260605-ee08fb8@sha256:4b6d2e78f8f6393ca0e8b23af21de50fc852c292cdd2c934cb2a05f31d6555cb`
- Docker build smoke: 5 tests passed inside image.
- Docker run full suite: 62 tests passed.
- Production reservations used one H200 GPU on one node and were cancelled when idle:
  - G009 final: `rsv-jeonghunpark-20260606-525828` cancelled.
  - G015 writer round-trip: `rsv-jeonghunpark-20260606-e183b7` cancelled.
  - Overlay sanity: `rsv-jeonghunpark-20260606-dac111` cancelled.
- Final pod check: no `jeonghunpark` pods active in `p-production` at final verification.
- W&B was not used because Phase 0 contained deterministic data/evaluator smokes, not model training or non-trivial learned evaluation.

## ROADMAP / DECISIONS terminal updates

- `docs/reproduction_spec/ROADMAP.md` Phase 0 checkboxes were updated from concrete evidence only, then refreshed after final review-fix evidence for the nested scale manifest; Phase 0.5 and later phases remain untouched.
- `docs/reproduction_spec/DECISIONS.md` finalized Phase 0 data/tokenization/evaluator/operational decisions, then refreshed after final review-fix evidence for nested scale construction and committed D2E reference-record parity; future VE/IDM/FDM training and harness decisions remain blank/deferred.

## Known limitations and deferrals

- No Generalist-IDM inference run was performed in Phase 0; only its public model id and official inference/evaluation path were located/versioned. Actual reference inference belongs to Phase 2.
- Held-out-game split is explicitly not selected in Phase 0; later model-evaluation phases must select held-out games before claiming held-out-game macro performance.
- Tokenized writer mouse metrics are intentionally not perfect due to deterministic 49x49 mouse quantization and aggregation; they are tokenizer/writer sanity evidence, not model quality.
- Overlay sanity sampled one Apex recording, not all 29 games.
- No VE, IDM, pseudo-label, FDM, feature-cache, or harness quality claims are made by Phase 0.

## Stop condition

Phase 0 is complete. The next work item is Phase 0.5 only if explicitly instructed; this run intentionally stops before Phase 0.5.
