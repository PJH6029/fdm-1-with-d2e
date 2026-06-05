# Ultragoal brief: Phase 0 data/evaluator foundation

Approved phase plan: `notes/plans/phase-0-data/20260605-data-foundation-plan.md`.
Research Architect review: `notes/plans/phase-0-data/reviews/20260605-research-architect-review-1.md`.
Research Critic review: `notes/plans/phase-0-data/reviews/20260605-research-critic-review-1.md` (`APPROVE`).
Ralplan escalation: none.

Run Phase 0 only. Do not advance into Phase 0.5. Keep `docs/reproduction_spec/ROADMAP.md` and `docs/reproduction_spec/DECISIONS.md` unchanged until concrete implementation/run/review evidence exists. All executable stories must be delegated to repo-local `research-executor` native subagents or `$team`; the phase supervisor owns Ultragoal checkpoints and terminal document updates.

Mandatory constraints: use `uv` for Python; default tests must be offline and not require live network, Hugging Face downloads, MLXP, or mounted D2E data; dataset `/mnt/ddn/extra-ddn-continuous-gui/` is read-only; generated artifacts must stay outside the dataset tree; before MLXP work, commit/push local changes, use production reservations within one node, use an immutable public Docker Hub image tag/digest under `docker.io/pjh6029/fdm-1-with-d2e`, pull in `/mnt/ddn/prod-runs/jeonghunpark/code/continuous-gui-poc/fdm-1-with-d2e`, record run evidence, and cancel idle pods.

Phase exit requires local tests/evidence, bounded real-D2E/MLXP manifest+reader+evaluator evidence, official evaluator invocation or deviation table, phase-exit GPT-Pro review and integration, final notes/run records, and evidence-backed ROADMAP/DECISIONS updates.
