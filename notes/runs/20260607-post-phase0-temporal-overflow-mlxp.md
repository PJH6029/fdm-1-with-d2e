# Post-Phase 0 MLXP run — 10s temporal sanity and K=8 overflow stats

Purpose: answer follow-up questions about per-bin temporal action sanity and whether the default `K=8` sparse event slots are adequate over the full D2E labeled dataset.

## Code / reservation

- Branch: `codex/phase-0`
- Git SHA: `b0a7e779ff753f27dc04913517fc629f3a75731a`
- Reservation: `rsv-jeonghunpark-20260607-1ef171`
- Project / namespace: `production` / `p-production`
- Node/GPU: node `5`, GPU `0`, one H200 GPU allocated; workload was CPU/data only.
- Image: `docker.io/pjh6029/fdm-1-with-d2e:phase0-20260605-ee08fb8@sha256:4b6d2e78f8f6393ca0e8b23af21de50fc852c292cdd2c934cb2a05f31d6555cb`
- Dataset root: `/mnt/ddn/extra-ddn-continuous-gui` (treated read-only; outputs outside dataset tree).
- Cluster repo: `/mnt/ddn/prod-runs/jeonghunpark/code/continuous-gui-poc/fdm-1-with-d2e`

## Local/cluster verification

Before reservation, local checks passed:

```bash
uv run --locked pytest -q  # 70 passed
uv run --locked python -m compileall src scripts tests
git diff --check
```

In the cluster clone:

```bash
uv run --locked pytest tests/unit/reporting tests/smoke/test_imports_and_cli_wrappers.py -q  # 10 passed
uv run --locked python -m compileall src scripts tests
```

## Artifacts

Local copied artifact bundle:

- `outputs/phase0/post-phase0-temporal-overflow/20260607-b0a7e77-temporal-overflow/summary.json`
- `outputs/phase0/post-phase0-temporal-overflow/20260607-b0a7e77-temporal-overflow/temporal_sanity_apex_10s/summary.json`
- `outputs/phase0/post-phase0-temporal-overflow/20260607-b0a7e77-temporal-overflow/temporal_sanity_apex_10s/bins.jsonl`
- `outputs/phase0/post-phase0-temporal-overflow/20260607-b0a7e77-temporal-overflow/temporal_sanity_apex_10s/frames/` (`200` PNGs)
- `outputs/phase0/post-phase0-temporal-overflow/20260607-b0a7e77-temporal-overflow/overflow_all_data_k8_parallel/overflow_summary.json`
- `outputs/phase0/post-phase0-temporal-overflow/20260607-b0a7e77-temporal-overflow/overflow_all_data_k8_parallel/recording_overflow_stats.jsonl`
- `outputs/phase0/post-phase0-temporal-overflow/20260607-b0a7e77-temporal-overflow/overflow_all_data_k8_parallel/progress.log`

MLXP API/script artifacts:

- `outputs/phase0/mlxp/20260607-temporal-overflow/`

## 10s temporal sanity result

Recording: `Apex_Legends/0805_01`.

The exporter auto-selected the densest keyboard-activity 10s window:

- bins: `15135..15334` (`200` bins)
- relative span from first screen: `756.75s..766.75s`
- frames exported: `200`
- tokenized bins: `200`, `tokens_per_bin=9`, `slots_per_bin=8`, `overflow_bin_count=0`

Keyboard replay:

- active keys at window start: `VK_87`
- active keys at window end: `VK_160`, `VK_87`
- active keys at recording end: none
- fresh key-down transitions started in the 10s window: `10`
- release statuses: `8` released inside the 10s window, `2` released after the window
- all fresh key-down transitions started in the window were released by recording end: `true`
- duplicate down events inside the window: `146` (held-key repeat behavior; not treated as independent fresh key-downs)
- unmatched up events inside the window: `0`; total recording unmatched up examples: `1` before the window (`VK_49`)

Visual spot check:

- `frames/bin_015144.png`: `VK_65:down` overlay on an Apex map/gameplay frame.
- `frames/bin_015182.png`: later `VK_65:up` overlay on gameplay frame.

## Full-dataset K=8 overflow result

Processed all discovered labeled recordings:

- recordings: `459`
- failures: `0`
- total 50ms bins: `19,057,088`
- nonempty sparse bins: `4,190,360`
- total sparse candidate tokens: `5,548,759`
- default `K=8` overflow bins: `27`
- `K=8` overflow fraction: `1.4167956825303006e-06` (~0.0001417% of bins)
- max sparse candidate tokens in one bin: `17`

K sweep:

| K | overflow bins | overflow fraction |
|---|---:|---:|
| 4 | 3,870 | 0.00020307404782934308 |
| 8 | 27 | 0.0000014167956825303006 |
| 12 | 1 | 0.00000005247391416778891 |
| 16 | 1 | 0.00000005247391416778891 |

Candidate-token histogram:

```json
{"0": 14866728, "1": 2952225, "2": 1145896, "3": 69846, "4": 18523, "5": 2561, "6": 984, "7": 242, "8": 56, "9": 18, "10": 6, "11": 2, "17": 1}
```

Overflow by game at K=8:

- `Apex_Legends`: `20 / 1,796,444` bins (`1.1133105178897867e-05`)
- `Ready_Or_Not`: `6 / 686,307` bins (`8.742443250615249e-06`)
- `Medieval_Dynasty`: `1 / 781,810` bins (`1.2790831531957893e-06`)
- all other games: `0`

Dropped token families in K=8 overflow bins:

- `scroll`: `50`
- `keyboard_down`: `20`
- `keyboard_up`: `2`

Interpretation: `K=8` is adequate for the current D2E labeled data by the Phase 0 overflow threshold (`0.1%`). Observed overflow is ~`0.0001417%`, far below threshold. The rare overflows are dominated by repeated held-key down events and scroll bursts; if later phases want zero-loss action reconstruction, `K=12` still leaves one pathological `17`-token repeat-down bin, so deduplicating repeat key-downs or compressing scroll bursts may be more efficient than raising K globally.

## Operational closeout

Reservation was cancelled after artifact copy and summary verification. No outputs were written into the dataset tree.
