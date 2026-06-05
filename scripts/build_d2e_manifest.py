#!/usr/bin/env python3
"""Build deterministic D2E dataset/split/scale manifests.

With no ``--dataset-root`` this wrapper emits an offline contract summary. When a
root is supplied, it discovers labeled ``.mkv``/``.mcap`` pairs and delegates all
manifest construction to ``fdm_1_with_d2e.data.manifests``. It does not parse
real MCAP contents or contact D2E/MLXP/network services.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fdm_1_with_d2e import __version__
from fdm_1_with_d2e.data import (
    DEFAULT_DATASET_NAME,
    MANIFEST_STORY_ID,
    build_dataset_manifest,
    build_held_out_game_split_manifest,
    build_scale_manifest,
    build_train_val_test_split_manifest,
    discover_labeled_recordings,
    load_json,
    stable_json_dumps,
    write_json_artifact,
)

DEFAULT_CONFIG = Path("configs/data/phase0_manifest_builders.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Committed builder config to record.")
    parser.add_argument("--dataset-root", help="D2E dataset root containing labeled/<game>/*.mkv|*.mcap.")
    parser.add_argument("--dataset-name", default=DEFAULT_DATASET_NAME)
    parser.add_argument("--output", help="Optional output path for the dataset manifest JSON.")
    parser.add_argument("--include-checksums", action="store_true", help="Compute sha256 checksums for video/MCAP files.")
    parser.add_argument("--duration-metadata", help="Optional JSON mapping recording_id to duration_ns or duration metadata.")
    parser.add_argument("--split-output", help="Optional output path for a train/validation/test split manifest.")
    parser.add_argument("--scale-output", help="Optional output path for scale subsets built from the split manifest.")
    parser.add_argument("--held-out-game", action="append", default=[], help="Game name to hold out; repeatable.")
    parser.add_argument("--optional-scale", type=int, action="append", default=[], help="Optional scale percentage, e.g. 1, 5, or 25.")
    parser.add_argument("--seed", type=int, default=0, help="Deterministic split/scale seed.")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    if args.dataset_root is None:
        payload = {
            "story_id": MANIFEST_STORY_ID,
            "package_version": __version__,
            "script": Path(__file__).name,
            "config": str(config_path),
            "config_exists": config_path.exists(),
            "status": "manifest_builders_available",
            "offline_only": True,
            "requires_dataset_root_for_build": True,
        }
        _emit(payload, json_mode=args.json)
        return 0

    dataset_root = Path(args.dataset_root)
    duration_metadata = load_json(args.duration_metadata) if args.duration_metadata else None
    recordings = discover_labeled_recordings(dataset_root)
    dataset_manifest = build_dataset_manifest(
        recordings,
        dataset_root=dataset_root,
        dataset_name=args.dataset_name,
        include_checksums=args.include_checksums,
        duration_metadata=duration_metadata,
    )

    written: dict[str, str] = {}
    if args.output:
        written["dataset_manifest"] = str(
            write_json_artifact(dataset_manifest, args.output, dataset_root=dataset_root)
        )

    split_manifest = None
    if args.split_output or args.scale_output:
        if args.held_out_game:
            split_manifest = build_held_out_game_split_manifest(
                dataset_manifest,
                args.held_out_game,
                seed=args.seed,
            )
        else:
            split_manifest = build_train_val_test_split_manifest(dataset_manifest, seed=args.seed)
        if args.split_output:
            written["split_manifest"] = str(
                write_json_artifact(split_manifest, args.split_output, dataset_root=dataset_root)
            )

    scale_manifest = None
    if args.scale_output:
        assert split_manifest is not None  # For type checkers; constructed above.
        scale_manifest = build_scale_manifest(
            split_manifest,
            dataset_manifest=dataset_manifest,
            optional_percentages=args.optional_scale,
            seed=args.seed,
        )
        written["scale_manifest"] = str(
            write_json_artifact(scale_manifest, args.scale_output, dataset_root=dataset_root)
        )

    if args.json:
        payload = {
            "dataset_manifest": dataset_manifest,
            "split_manifest": split_manifest,
            "scale_manifest": scale_manifest,
            "written": written,
        }
        print(stable_json_dumps(payload), end="")
    else:
        print(
            f"recordings={dataset_manifest['recording_count']} games={dataset_manifest['game_count']} "
            f"manifest_id={dataset_manifest['manifest_id']} written={written}"
        )
    return 0


def _emit(payload: dict[str, object], *, json_mode: bool) -> None:
    if json_mode:
        print(stable_json_dumps(payload), end="")
    else:
        print(f"{payload['script']}: {payload['status']} (config={payload['config']})")


if __name__ == "__main__":
    raise SystemExit(main())
