# Research Architect review 1 — Phase 0 data foundation

## Verdict recommendation

`REVISE_NEEDED` — no ralplan escalation needed.

## Required fixes before Ultragoal

1. Make real D2E/MLXP evidence a required Phase 0 exit story, not optional. Synthetic fixtures can test contracts, but cannot prove real OWAMcap schema, timestamp alignment, full manifest IDs, or action-distribution decisions.
2. Add a required real-data manifest/action-distribution pass for exact dataset root, recording list, durations, game names, split/scale subsets, checksums/sizes, no-op/action distributions, mouse magnitude distributions, and overflow rates.
3. Strengthen official evaluator compatibility evidence: require official `evaluate.py` invocation on generated/real MCAP fixture or a recorded deviation table. Upstream D2E HEAD verified as `80e98e26e4dc584ec76fec5789b4a97c275dd032`; official evaluator uses 50ms bins and decoded `dx/dy`, so adapter normalization is a coupling risk.
4. Avoid network-dependent default tests. Keep `uv run pytest` offline/pinned; put live GitHub/Hugging Face HEAD checks under an external smoke/run-record path.
5. Add missing Phase 0 reference/floor artifact coverage, especially an initial FDM-1 target-gap rubric draft as an explicit Ultragoal story/artifact.

## Evidence references

- `notes/plans/phase-0-data/20260605-data-foundation-plan.md`: strong structure, correct Phase 0/0.5 boundary, but made real D2E validation optional.
- `docs/reproduction_spec/ROADMAP.md` Phase 0: requires real labeled reader, sampled-recording timestamp/overlay checks, GT evaluator round-trip, manifests, action distributions, and reference/floor artifacts.
- `docs/reproduction_spec/CANONICAL_SPEC.md`: Gate 0 requires D2E reader, 50ms binning, official-style metrics, committed split/scale manifests.
- `docs/reproduction_spec/spec/data_and_actions.md`: fixes 50ms bins, `K=8`, overflow policy, train-split mouse-bin fitting, and visual timestep metadata/causality concerns.
- `docs/reproduction_spec/spec/evaluation.md`: requires official evaluator path whenever possible and deviation recording for local wrappers.
- `docs/reproduction_spec/OPERATIONAL_RULES.md`: supports read-only dataset, MLXP, immutable image, artifact-path, and W&B rules.
