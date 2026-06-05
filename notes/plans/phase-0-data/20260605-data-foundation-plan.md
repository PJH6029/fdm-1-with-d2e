# Phase plan: Phase 0 data/evaluator foundation

## Scope

Build the deterministic Phase 0 foundation for the FDM-1/D2E reproduction without advancing into Phase 0.5. Scope is limited to reusable data/action/evaluation infrastructure, local fixture evidence, official D2E reference path/versioning, and phase-exit review. Later VE/IDM/FDM training stays out of scope except for floor/scaffold availability required by the Phase 0 roadmap.

Core deliverables:

- D2E/OWAMcap labeled recording reader API for `.mkv` + `.mcap` pairs.
- 60fps-to-50ms video timestep sampler policy.
- 50ms mouse/keyboard/button/scroll event binning.
- action tokenizer/de-tokenizer with fixed mouse/event slots, special tokens, and overflow accounting.
- prediction-to-event/MCAP-compatible writer path or dependency-gated adapter.
- deterministic dataset/split/scale/action-distribution manifest builders.
- local D2E-style evaluator-compatible round-trip metrics and official evaluator path/version record.
- local fixtures, tests, and notes/run records proving the interfaces.
- floor/scaffold availability for later IDM/FDM/VE phases as explicit placeholder contracts only, not quality claims.

Out of scope:

- Phase 0.5 thin E2E spine.
- VE finetuning, IDM implementation, FDM implementation, pseudo-label generation, base-scale training, or quality claims.
- Writing anything into `/mnt/ddn/extra-ddn-continuous-gui/`.

## Current spec/evidence

Local spec inspected:

- `AGENTS.md` and `docs/reproduction_spec/AGENTS.md` require the repo-local reproduction loop, delegated execution, `uv`, evidence packets, and ROADMAP/DECISIONS updates only after evidence.
- `docs/reproduction_spec/CANONICAL_SPEC.md` Gate 0 requires labeled D2E reader, 50ms action binning, plausible overlays, official-style metrics, and committed split/scale manifests.
- `docs/reproduction_spec/OPERATIONAL_RULES.md` requires local edit/check, commit/push before MLXP work, read-only D2E path, custom immutable Docker image for cluster work, W&B for non-trivial training/eval, and cancellation of idle pods.
- `docs/reproduction_spec/spec/data_and_actions.md` fixes non-overlapping 50ms bins, default `K=8`, raw HID mouse delta aggregation, 49 signed exponential bins per axis, key/button/scroll tokens, special tokens, and overflow logging.
- `docs/reproduction_spec/spec/evaluation.md` fixes D2E primary metrics and aggregate/reporting requirements.
- `docs/reproduction_spec/ROADMAP.md` Phase 0 is entirely unchecked before this phase.
- `docs/reproduction_spec/DECISIONS.md` has open slots for data/tokenization/evaluation/reference paths.

Current repo evidence:

- Branch: `codex/phase-0`.
- Current repo has docs, literature survey, and repo-local agents/skills only. No implementation package, tests, configs, or schemas exist yet.
- Existing literature files include `D2E.md`, `FDM-1.md`, `MASKED_DIFFUSION.md`, and `VIDEO_ENCODER.md`.

External upstream evidence checked on 2026-06-05:

- Official D2E GitHub repo `worv-ai/D2E` HEAD: `80e98e26e4dc584ec76fec5789b4a97c275dd032`.
- Upstream README says D2E 480p includes 267 hours, 29 games, 480p/60fps H.264 video, keyboard/mouse/window input events in OWAMcap/MCAP.
- Upstream `evaluate.py` is released and computes D2E metrics over non-overlapping 50ms bins.
- Upstream `inference.py` defaults to `open-world-agents/Generalist-IDM-1B`, uses `uv`, and outputs predicted MCAP. Public README examples run `uv run inference.py gameplay.mp4 predicted.mcap --max-duration 30` and `uv run evaluate.py ground_truth.mcap predicted.mcap --output results.json`.

## Literature and GPT-Pro artifacts used

Initial GPT-Pro query: none. Phase 0 has no mandatory pre-implementation GPT-Pro gate; local specs and official D2E upstream are sufficient for initial implementation. The mandatory phase-exit GPT-Pro review remains a terminal Ultragoal story and must be run before declaring Phase 0 complete.

Existing survey artifacts used:

- `docs/literature_survey/D2E.md` for D2E dataset/evaluator/OWAMcap anchors.
- `docs/literature_survey/FDM-1.md` for action-token semantics and floor scaffold boundaries.

Primary-source checks used:

- `https://github.com/worv-ai/D2E` README, `evaluate.py`, `inference.py` at HEAD `80e98e26e4dc584ec76fec5789b4a97c275dd032`.
- `https://huggingface.co/open-world-agents/Generalist-IDM-1B` model card path.
- `https://huggingface.co/datasets/open-world-agents/D2E-480p` dataset path.

## Agent interpretation and hypotheses

Hypotheses:

1. Phase 0 should be built contract-first locally with synthetic MCAP-like fixtures, but Phase 0 exit also requires a bounded real-D2E/MLXP evidence pass. Synthetic fixtures can prove local contracts; they cannot prove real OWAMcap schema compatibility, timestamp/overlay plausibility, full dataset manifests, per-game distributions, or official evaluator round-trip behavior on real recordings.
2. Official evaluator compatibility should be represented as both a local D2E-style metric implementation and a versioned upstream path/command record; Phase 0 exit requires official `evaluate.py` invocation on a generated/real MCAP fixture when practical, or an explicit deviation/blocker table if exact invocation cannot run.
3. For serious reproduction continuity, Phase 0 should not create monolithic scripts. Reusable modules, committed configs, JSON schemas, thin CLI wrappers, and unit/integration tests are the correct foundation for later phases.
4. Floor/scaffold availability in Phase 0 should mean importable placeholders and schemas for no-op/action-frequency/action-only/video-only diagnostics, plus an explicit initial FDM-1 target-gap rubric draft, not trained models or Phase 0.5 spine completion.

Known uncertainty:

- Local environment may lack `mcap-owa-support`, `owa-msgs`, `ffmpeg`, and real D2E files. Code should degrade clearly with optional dependency errors while tests use dependency-light fixtures.
- The official OWAMcap decoded field names vary across upstream code snippets (`last_x/last_y` vs evaluator `dx/dy`). The adapter should normalize both and test both forms.
- Keyboard virtual-key naming must be kept stable but may need a later real-data audit for exact key identifiers.

## Proposed implementation direction

Repository structure to create:

- `pyproject.toml` for `uv`-managed package/test dependencies.
- `src/fdm_1_with_d2e/` package with focused modules:
  - `data/types.py`: canonical dataclasses for recordings, events, bins, manifests.
  - `data/reader.py`: recording discovery and optional OWAMcap reader adapter.
  - `data/binning.py`: 50ms bin creation, event assignment, video sampler policy, action aggregation.
  - `data/manifests.py`: dataset, split, scale, and per-game action distribution manifests.
  - `tokenization/action_vocab.py`: special tokens and 49-bin signed exponential mouse quantizer.
  - `tokenization/actions.py`: tokenize/de-tokenize bins with `K=8`, overflow accounting, and deterministic ordering.
  - `evaluation/d2e_metrics.py`: local D2E-style mouse/keyboard/button metric computation from canonical event bins.
  - `evaluation/roundtrip.py`: prediction-to-events round-trip checks.
  - `evaluation/official.py`: versioned official D2E `evaluate.py` / `inference.py` path record, command builders, and local deviation table support.
  - `models/floors.py`: no-op/action-frequency/previous-action/action-only/video-only placeholder classes or callable stubs for later phases.
  - `video/scaffold.py`: frozen-encoder probe scaffold placeholder with explicit not-implemented boundary.
  - `harness/safety.py`: event writer safety/state guard utilities as needed by writer tests.
- `scripts/` thin CLIs over package code:
  - `build_d2e_manifest.py`
  - `summarize_action_distribution.py`
  - `d2e_roundtrip_check.py`
  - `locate_d2e_reference.py`
  - `draft_phase0_target_gap_rubric.py` or equivalent reporting module output
- `configs/` defaults:
  - `configs/data/phase0_manifest.yaml`
  - `configs/tokenization/default.yaml`
  - `configs/evaluation/d2e_local.yaml`
  - `configs/experiments/phase-0-data/fixture_roundtrip.yaml`
- `schemas/` JSON schemas for dataset manifest, split manifest, scale manifest, action distribution, tokenizer metadata, evaluator metrics, and D2E reference record.
- `tests/unit/`, `tests/integration/`, `tests/smoke/` with fixture-only tests.
- `notes/runs/20260605-phase0-local-evidence.md` run/evidence record.

Implementation stories should be delegated to `research-executor` workers with disjoint write scopes:

1. package/config/bootstrap + schemas;
2. reader/binning/manifests;
3. tokenizer/de-tokenizer/writer/evaluator;
4. floor/reference scaffolds, tests, notes, and final integration.

The supervisor owns Ultragoal ledger/checkpoints and ROADMAP/DECISIONS updates only after verified evidence.

## Proposed experiment / ablation matrix

Phase 0 is test/evidence based, not model-quality ablation based.

Required local checks:

- Unit tests for 50ms bins, boundary conditions, video sampling policy, event ordering, overflow policy, and scroll/button/key normalization.
- Unit tests for mouse quantizer round-trip and zero/signed bin behavior.
- Unit tests for tokenizer/de-tokenizer preserving sparse events and producing fixed slots.
- Integration test for GT action round-trip through tokenization, de-tokenization, writer-compatible events, and local D2E-style metrics.
- Manifest tests for deterministic train/val/test, held-out game, and 10/50/100 scale subsets.
- Reference-path test that records a pinned upstream D2E GitHub revision and command templates without downloading model weights or requiring network in the default test suite.
- Artifact write-protection test that rejects output paths inside the configured dataset root.
- Target-gap rubric artifact test or review check proving the draft exists and is explicitly non-final.

Required real-D2E/MLXP checks before Phase 0 exit:

- Run a bounded real-data manifest/action-distribution pass from the MLXP-mounted D2E dataset using the required operational preflight, committed/pushed git SHA, immutable image tag/digest, and a run record. This pass must record dataset root, recording list, durations, game names, split/scale subsets, checksums/sizes, no-op/action distributions, raw mouse magnitude distributions, and overflow rates outside the dataset tree.
- Run a small real-recording reader/timestamp/evaluator compatibility smoke, including official `evaluate.py` invocation on a generated or round-tripped MCAP when practical. If exact official invocation is blocked by dependency/schema issues, produce a deviation table with the blocker, local wrapper behavior, and the minimum follow-up needed.

## Success gate

Phase 0 is evidence-complete when all are true:

- Offline `uv run pytest` passes for unit/integration/smoke tests created for Phase 0; default tests must not require live network, Hugging Face downloads, MLXP, or the D2E dataset.
- Local fixture evidence demonstrates canonical 50ms binning, tokenization/de-tokenization, writer-compatible event reconstruction, and local D2E-style GT round-trip sanity metrics.
- Real-D2E MLXP evidence demonstrates labeled reader compatibility, timestamp/action sanity on sampled recordings, committed manifest generation, split/scale construction, per-game action distributions, raw mouse magnitude distributions, and overflow accounting without writing to the dataset tree.
- Official D2E Generalist-IDM/evaluator path is located/versioned with upstream commit SHA, model/dataset IDs, and `uv run` command templates. Official `evaluate.py` is invoked on a generated/real MCAP fixture when practical; otherwise a deviation table records every blocker and local wrapper difference.
- Floor/scaffold availability exists as explicit importable placeholder contracts for later phases, with no quality claims.
- Initial FDM-1 target-gap rubric draft exists as a Phase 0 artifact and is labeled as a draft pending later FDM/harness evidence.
- Notes/run records capture local commands, MLXP real-data commands, artifacts, evidence, known limitations, image/tag/digest details when cluster is used, and pod cancellation status when applicable.
- Mandatory phase-exit GPT-Pro review is saved and integrated.
- `ROADMAP.md` and `DECISIONS.md` are updated only from the concrete evidence above.

## Failure / fallback criteria

- If optional OWAMcap dependencies cannot be installed locally, keep the adapter optional for local tests but still schedule a bounded MLXP real-D2E smoke before Phase 0 exit.
- If official evaluator formulas differ from the local implementation, record the deviation and prefer invoking/versioning official `evaluate.py` for headline metrics.
- If event overflow exceeds the 0.1% target on real data, leave Phase 0 status partial/blocked for that item and record a K={8,16} follow-up; do not silently change default `K=8`.
- If GPT-Pro phase-exit review rejects sufficiency, add/redispatch the minimum evidence story it requires before final ROADMAP/DECISIONS updates.

## Cluster execution plan

Default Phase 0 path is local implementation plus a required bounded real-D2E/MLXP evidence pass before phase exit:

1. Use `uv run ...` for all Python commands.
2. Keep generated local artifacts under ignored project paths (`outputs/`, `runs/`) or committed tiny fixtures only where tests require them.
3. Do not write into `/mnt/ddn/extra-ddn-continuous-gui/`.
4. Before the required MLXP real-data pass:
   - commit and push local changes first;
   - reserve smallest efficient production pod, likely 1 GPU or CPU-capable image if supported, within one node;
   - use public Docker Hub image `docker.io/pjh6029/fdm-1-with-d2e:<role>-20260605-<gitsha>` and record digest;
   - pull the commit in `/mnt/ddn/prod-runs/jeonghunpark/code/continuous-gui-poc/fdm-1-with-d2e`;
   - run only bounded manifest/distribution/reader/evaluator smoke commands against read-only D2E input;
   - store artifacts outside the dataset tree;
   - cancel the pod when idle.
5. W&B is not required for local fixture tests; use the canonical entity/project for any non-trivial cluster evaluation.

## Review result

- Research Architect review: `notes/plans/phase-0-data/reviews/20260605-research-architect-review-1.md` (`REVISE_NEEDED`, no ralplan; revisions integrated to require real-D2E/MLXP exit evidence, official evaluator evidence/deviation table, offline default tests, and target-gap rubric story).
- Research Critic verdict: `notes/plans/phase-0-data/reviews/20260605-research-critic-review-1.md` (`APPROVE`).
- Ralplan escalation: none; critic approved direct Ultragoal after revisions.

## Decision slots to fill after evidence

Potential `DECISIONS.md` slots after Phase 0 evidence:

- D2E dataset revision / local manifest ID.
- Train/val/test split policy.
- Held-out-game split.
- Scale subset construction.
- Active window metadata policy.
- Mouse bin fitting data.
- Scroll representation.
- Overflow threshold/action.
- D2E-Generalist-IDM-1B reference checkpoint/revision.
- Generalist-IDM inference command/path.
- Generalist-IDM evaluation compatibility notes.
- FDM-1 target-gap rubric draft path.
- FDM causal input alignment / visual cutoff draft for later guardrails.
- Evaluator revision.
- Artifact storage and run-record locations.
