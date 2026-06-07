#!/usr/bin/env python3
"""Summarize D2E sparse action-token overflow rates for K-slot tokenization."""

from __future__ import annotations

import argparse
from pathlib import Path

from fdm_1_with_d2e import __version__
from fdm_1_with_d2e.data import stable_json_dumps
from fdm_1_with_d2e.reporting.overflow_stats import DEFAULT_K_SWEEP, availability_payload, summarize_dataset_overflow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", help="D2E dataset root containing labeled recordings.")
    parser.add_argument("--output-dir", help="Output artifact directory outside the dataset tree.")
    parser.add_argument("--slots-per-bin", type=int, default=8, help="Default sparse event-slot count K.")
    parser.add_argument("--k-sweep", type=int, action="append", default=[], help="Additional/alternative K value to evaluate; repeatable.")
    parser.add_argument("--limit-recordings", type=int, help="Optional bounded smoke limit.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.dataset_root is None and args.output_dir is None:
        payload = {**availability_payload(), "package_version": __version__, "script": Path(__file__).name}
        print(stable_json_dumps(payload), end="" if args.json else "\n")
        return 0
    if args.dataset_root is None or args.output_dir is None:
        parser.error("--dataset-root and --output-dir are required for real overflow stats")

    k_sweep = tuple(args.k_sweep) if args.k_sweep else DEFAULT_K_SWEEP
    summary = summarize_dataset_overflow(
        dataset_root=args.dataset_root,
        output_dir=args.output_dir,
        slots_per_bin=args.slots_per_bin,
        k_sweep=k_sweep,
        limit_recordings=args.limit_recordings,
    )
    payload = {"status": "overflow_stats_written", "summary": summary}
    if args.json:
        print(stable_json_dumps(payload), end="")
    else:
        aggregate = summary["aggregate"]
        print(
            f"{Path(__file__).name}: {payload['status']} "
            f"recordings={summary['recording_count_processed']} "
            f"overflow={aggregate['overflow_bin_count']}/{aggregate['bin_count']} "
            f"out={summary['output_dir']}"
        )
    return 1 if summary["failure_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
