#!/usr/bin/env python3
"""Summarize per-game action distributions from offline canonical-bin JSON.

The wrapper consumes a dataset manifest plus a fixture/action-bin JSON mapping
recording IDs to canonical 50ms bins. Real D2E MCAP decoding remains a later
MLXP story; this script stays a thin package-code wrapper with no network or
cluster side effects.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from fdm_1_with_d2e import __version__
from fdm_1_with_d2e.data import (
    MANIFEST_STORY_ID,
    action_bins_from_jsonable,
    build_action_distribution_manifest,
    load_json,
    stable_json_dumps,
    write_json_artifact,
)

DEFAULT_CONFIG = Path("configs/data/phase0_manifest_builders.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Committed builder config to record.")
    parser.add_argument("--dataset-manifest", help="Dataset manifest JSON produced by build_d2e_manifest.py.")
    parser.add_argument("--bins-json", help="JSON mapping recording_id to canonical ActionBin fixture dictionaries.")
    parser.add_argument("--output", help="Optional output path for the action-distribution manifest.")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    if args.dataset_manifest is None or args.bins_json is None:
        payload = {
            "story_id": MANIFEST_STORY_ID,
            "package_version": __version__,
            "script": Path(__file__).name,
            "config": str(config_path),
            "config_exists": config_path.exists(),
            "status": "action_distribution_builder_available",
            "offline_only": True,
            "requires_dataset_manifest_and_bins_json": True,
        }
        _emit(payload, json_mode=args.json)
        return 0

    dataset_manifest = load_json(args.dataset_manifest)
    bins_payload = load_json(args.bins_json)
    recording_bins = action_bins_from_jsonable(bins_payload)
    distribution = build_action_distribution_manifest(dataset_manifest, recording_bins)

    written: dict[str, str] = {}
    if args.output:
        written["action_distribution"] = str(
            write_json_artifact(distribution, args.output, dataset_root=dataset_manifest.get("dataset_root"))
        )

    if args.json:
        print(stable_json_dumps({"action_distribution": distribution, "written": written}), end="")
    else:
        print(
            f"recordings={distribution['recording_count']} games={distribution['game_count']} "
            f"manifest_id={distribution['manifest_id']} written={written}"
        )
    return 0


def _emit(payload: dict[str, object], *, json_mode: bool) -> None:
    if json_mode:
        print(stable_json_dumps(payload), end="")
    else:
        print(f"{payload['script']}: {payload['status']} (config={payload['config']})")


if __name__ == "__main__":
    raise SystemExit(main())
