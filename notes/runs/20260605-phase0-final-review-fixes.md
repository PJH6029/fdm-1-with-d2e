# Phase 0 final review fixes

Date: 2026-06-05 / 2026-06-06 KST  
Scope: Phase 0 terminal quality-gate fixes only. This note does not start Phase 0.5.

## Trigger

The final independent code-reviewer lane returned `REQUEST CHANGES` with two findings:

1. Stratified scale subsets were not guaranteed nested because each percentage used a different per-game shuffle salt.
2. `configs/data/d2e_reference.json` was stale relative to the updated default official-reference builder after G015 writer-produced MCAP evidence.

## Fixes

- `src/fdm_1_with_d2e/data/manifests.py` now uses one stable per-game scale ordering independent of percentage, so smaller percentages are prefixes of larger percentages.
- `tests/unit/data/test_manifests.py` adds a regression for `5% <= 10% <= 50% <= 100%` nesting across enough per-game samples.
- `configs/data/d2e_reference.json` was regenerated from `build_official_reference_record()`.
- `tests/unit/evaluation/test_official_reference.py` now enforces committed reference-record parity with the default builder.

## Real-manifest-derived scale proof

Using the copied real-D2E artifacts from the G009 MLXP run, not the dataset tree:

- Source dataset manifest: `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/artifacts/dataset_manifest.json`
- Source split manifest: `outputs/phase0/real-d2e-smoke/20260605-g009-f801bce/artifacts/split_manifest.json`
- Regenerated nested scale manifest: `outputs/phase0/final-review-fixes/20260605-g014-47cb959/nested_scale_manifest.json`
- Proof JSON: `outputs/phase0/final-review-fixes/20260605-g014-47cb959/nested_scale_manifest_proof.json`

Regenerated scale manifest ID: `phase0-scale-d32d102e3412cfbe`

Counts remain unchanged from the earlier real-D2E evidence:

- `5_percent`: `36`
- `10_percent`: `50`
- `50_percent`: `193`
- `100_percent`: `367`

Nesting proof:

- `5_percent` subset of `10_percent`: `true`
- `10_percent` subset of `50_percent`: `true`
- `50_percent` subset of `100_percent`: `true`

Previous non-nested scale manifest ID from the G009 run: `phase0-scale-726895836126a6ef`. It remains historical run evidence, but terminal Phase 0 decisions and roadmap now cite the regenerated nested scale manifest above.

## Verification

Verification was rerun after the fixes and is recorded in the final quality gate artifacts.
