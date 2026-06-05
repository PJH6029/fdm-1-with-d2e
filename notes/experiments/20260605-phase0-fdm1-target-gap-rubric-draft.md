# Initial FDM-1 target-gap rubric draft (NON-FINAL)

Rubric id: `phase0-fdm1-target-gap-rubric-draft-v0`
Status: `non_final_draft_no_success_claim`
Created by story: `G006-implement-floor-and-probe-scaffolds`
Not a success claim: `true`

**NON-FINAL DRAFT: this rubric is not a reproduction success claim, not a trained-model evaluation, and not a replacement for later FDM/free-running/harness evidence.**

## Source basis

- `docs/reproduction_spec/CANONICAL_SPEC.md`
- `docs/reproduction_spec/spec/evaluation.md`
- `docs/literature_survey/FDM-1.md`
- `docs/literature_survey/D2E.md`

## Draft criteria

### 1. Public recipe and action-token alignment

- Criterion id: `recipe_alignment`
- Question: Does the local FDM training path match the public VE -> IDM pseudo-labeling -> FDM recipe and action-token semantics closely enough to compare gaps?
- Public/spec basis: Public/local spec describes interleaved video/action FDM training on IDM-labeled videos, keyboard press/release, scroll, 49x49 mouse bins, no-op handling, and optional next-click evidence.
- Current status: `not_evaluated_phase0_draft_only`
- Finality: `non_final_draft_no_success_claim`
- Success-claim policy: `cannot_support_success_claim_without_later_verified_fdm_evidence`
- Local evidence required:
  - Committed tokenizer/action-vocab revision and prediction-to-event conversion revision.
  - Run record showing GT/pseudo/filtered-pseudo/mix data source for each FDM checkpoint.
  - Explicit list of unmatched public ingredients such as transcripts/language grounding or private corpus scale.

### 2. Causal FDM input alignment

- Criterion id: `causal_input_alignment`
- Question: Does the FDM predict action bin [t,t+50ms) without visual evidence after decision time t?
- Public/spec basis: Canonical FDM spec requires strict no-future-visual alignment before any FDM metric can be trusted.
- Current status: `not_evaluated_phase0_draft_only`
- Finality: `non_final_draft_no_success_claim`
- Success-claim policy: `cannot_support_success_claim_without_later_verified_fdm_evidence`
- Local evidence required:
  - No-future-visual leakage guard test for the chosen visual-bin indexing policy.
  - Feature-cache metadata showing source frame span, decision time, and causal-safety flag.
  - Failure note if any model used target-interval or future frames.

### 3. D2E offline action quality against floor diagnostics

- Criterion id: `d2e_offline_action_quality`
- Question: Does a trained FDM beat no-op, previous-action, action-only, and video-only diagnostics on reproducible D2E action metrics without hiding per-game regressions?
- Public/spec basis: D2E evaluation uses non-overlapping 50ms bins with mouse Pearson/scale and keyboard/mouse-button accuracy; FDM spec adds NLL, sparse F1, and no-op FP/FN.
- Current status: `not_evaluated_phase0_draft_only`
- Finality: `non_final_draft_no_success_claim`
- Success-claim policy: `cannot_support_success_claim_without_later_verified_fdm_evidence`
- Local evidence required:
  - Teacher-forced NLL/CE by token family.
  - D2E-style action metrics after prediction-to-event/MCAP-compatible conversion.
  - Sparse event precision/recall/F1, no-op FP/FN, per-game macro, held-out-game macro, and floor-baseline comparisons.

### 4. Pseudo-label usefulness

- Criterion id: `pseudo_label_usefulness`
- Question: Do IDM pseudo-labels retain useful FDM performance relative to GT labels, and does filtering improve quality/coverage?
- Public/spec basis: The public recipe trains FDM on IDM-labeled videos; canonical spec requires FDM-GT, FDM-Pseudo, FDM-FilteredPseudo, and FDM-Mix comparisons.
- Current status: `not_evaluated_phase0_draft_only`
- Finality: `non_final_draft_no_success_claim`
- Success-claim policy: `cannot_support_success_claim_without_later_verified_fdm_evidence`
- Local evidence required:
  - FDM-Pseudo/FDM-FilteredPseudo/FDM-Mix metrics relative to FDM-GT on the same split/budget.
  - Pseudo-label confidence/coverage curves and no-op/event-rate drift.
  - Filtering threshold and low-confidence handling run records.

### 5. Logged free-running stability

- Criterion id: `logged_free_running_stability`
- Question: When predicted previous actions are fed back while logged video is fixed, does behavior remain stable over horizon?
- Public/spec basis: Evaluation spec requires free-running degradation, action spam, no-op collapse, key/button violations, and mouse drift before final FDM claims.
- Current status: `not_evaluated_phase0_draft_only`
- Finality: `non_final_draft_no_success_claim`
- Success-claim policy: `cannot_support_success_claim_without_later_verified_fdm_evidence`
- Local evidence required:
  - Per-horizon degradation curves using predicted previous actions.
  - No-op collapse/action-spam rates, key/button state violations, mouse drift, and representative failure clips/logs.
  - Comparison to floor diagnostics under identical replay-control conditions.

### 6. Comparable harness behavior categories

- Criterion id: `harness_behavior_categories`
- Question: Where local desktop/game or replay-control harness scenarios overlap public FDM-1 behavior categories, what succeeds, fails, or remains non-comparable?
- Public/spec basis: The FDM-1 survey records public/post-aligned categories including Typing Test, Verbal Memory, Symbolic Memory, and Target Accuracy; canonical spec requires stable harness behavior.
- Current status: `not_evaluated_phase0_draft_only`
- Finality: `non_final_draft_no_success_claim`
- Success-claim policy: `cannot_support_success_claim_without_later_verified_fdm_evidence`
- Local evidence required:
  - Scenario definitions, seeds, run duration, action count/rate, invalid actions, stuck states, drift/explosion, crash/hang, and simple task/sanity success.
  - Category-level mapping table explaining which public categories are comparable locally.
  - Failure analysis for UI/text/cursor/crosshair or game-state perception issues.

### 7. Data/model scale and efficiency gap

- Criterion id: `scale_and_efficiency_gap`
- Question: How much of the remaining gap is explained by D2E data scale, model scale, context length, VE compression, and throughput?
- Public/spec basis: Canonical spec says the closed FDM-1 data/model/eval details are unavailable and warns against claiming parity with private-scale systems without direct evidence.
- Current status: `not_evaluated_phase0_draft_only`
- Finality: `non_final_draft_no_success_claim`
- Success-claim policy: `cannot_support_success_claim_without_later_verified_fdm_evidence`
- Local evidence required:
  - IDM/FDM scaling curves at required D2E scales and selected optional low-scale points.
  - Model parameter count, context length, feature-cache cost, GPU throughput, and inference latency records.
  - Explicit non-comparable gap list for private data, model details, transcripts/language grounding, and closed harness/evaluator differences.

## Phase 0 interpretation

This artifact only fixes the vocabulary of later target-gap evidence. It does not evaluate a local FDM,
does not compare against the closed-source FDM-1 checkpoint, and does not complete any Phase 4/6 success gate.
Later reports must replace `not_evaluated_phase0_draft_only` entries with run-record-backed metrics,
failure cases, and explicit non-comparable gaps.
