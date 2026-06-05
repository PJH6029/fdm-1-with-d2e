# GPT-Pro thread anchor — Phase 0 data/evaluator exit review

Phase: Phase 0 — data pipeline, evaluator, and sanity checks for the FDM-1/D2E reproduction.

Topic: Decide whether the Phase 0 evidence is sufficient to exit Phase 0 and move to Phase 0.5, or whether there is a minimal additional data/evaluator smoke that should block exit.

Stable assumptions:
- This is a serious D2E-based reproduction of FDM-1, not a PoC.
- Phase 0 does not train VE/IDM/FDM models; it must establish reproducible data, tokenization, manifests, evaluator, and sanity scaffolds.
- D2E dataset path is read-only; GPU/data runs happen on MLXP; generated outputs stay outside the dataset tree.
- Phase 0.5 starts only after explicit user instruction; this thread only judges Phase 0 evidence.

Stale-thread conditions:
- New real-D2E run changes manifest counts, schema behavior, or official evaluator status.
- Tokenization/action schema policy changes materially.
- Phase 0.5 or VE/IDM/FDM training evidence becomes the active review target.
