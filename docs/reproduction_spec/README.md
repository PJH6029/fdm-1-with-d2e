# FDM-1 with D2E Reproduction Docs

Read these files in order:

1. [`CANONICAL_SPEC.md`](./CANONICAL_SPEC.md) — research/reproduction spec and success gates.
2. [`OPERATIONAL_RULES.md`](./OPERATIONAL_RULES.md) — how to execute the work on local + MLXP cluster resources.
3. [`DECISIONS.md`](./DECISIONS.md) — final reproduction decisions as they are made.
4. [`ROADMAP.md`](./ROADMAP.md) — phase-by-phase checklist for implementation, ablations, evaluation, artifacts, and progress tracking.
5. [`spec/`](./spec/) — component/protocol details that must remain consistent with the canonical spec.

Active component specs:

- [`spec/data_and_actions.md`](./spec/data_and_actions.md) — D2E data contract, 50ms bins, action tokenization.
- [`spec/video_encoder.md`](./spec/video_encoder.md) — video encoder candidates, adaptation, and promotion.
- [`spec/idm.md`](./spec/idm.md) — IDM objective, masked diffusion candidates, pseudo-labeling.
- [`spec/fdm.md`](./spec/fdm.md) — FDM objective, causal prediction, pseudo-label training.
- [`spec/evaluation.md`](./spec/evaluation.md) — metric definitions, aggregation, and minimal eval matrix.

The goal is a serious D2E-based reproduction of the public FDM-1 training recipe, not a smoke-test PoC. When component docs disagree, `CANONICAL_SPEC.md` wins and the component doc should be repaired.
