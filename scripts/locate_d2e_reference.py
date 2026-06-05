#!/usr/bin/env python3
"""Emit the pinned official D2E reference-path record without network access."""

from __future__ import annotations

import argparse
from pathlib import Path

from fdm_1_with_d2e import __version__
from fdm_1_with_d2e.evaluation import (
    DEFAULT_REFERENCE_CONFIG,
    build_evaluate_command,
    build_inference_command,
    build_official_reference_record,
    load_official_reference_record,
    reference_summary,
    shell_join,
    stable_json_dumps,
    write_official_reference_record,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_REFERENCE_CONFIG), help="Committed D2E reference JSON record.")
    parser.add_argument("--emit-default", action="store_true", help="Emit the built-in pinned record instead of reading --config.")
    parser.add_argument("--write-output", help="Optional path to write the emitted record as stable JSON.")
    parser.add_argument("--video-path", default="gameplay.mp4", help="Example gameplay input path for command rendering.")
    parser.add_argument("--predicted-mcap", default="predicted.mcap", help="Example predicted MCAP path for command rendering.")
    parser.add_argument("--ground-truth-mcap", default="ground_truth.mcap", help="Example ground-truth MCAP path for command rendering.")
    parser.add_argument("--results-json", default="results.json", help="Example official evaluator output path.")
    parser.add_argument("--max-duration", default="30", help="Example inference max duration seconds.")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    if args.emit_default or not config_path.exists():
        record = build_official_reference_record()
        config_exists = config_path.exists()
    else:
        record = load_official_reference_record(config_path)
        config_exists = True

    rendered_commands = {
        "inference": shell_join(
            build_inference_command(args.video_path, args.predicted_mcap, max_duration_seconds=args.max_duration)
        ),
        "evaluate": shell_join(build_evaluate_command(args.ground_truth_mcap, args.predicted_mcap, args.results_json)),
    }
    payload = {
        "package_version": __version__,
        "script": Path(__file__).name,
        "config": str(config_path),
        "config_exists": config_exists,
        **reference_summary(record),
        "rendered_commands": rendered_commands,
        "record": record,
    }

    if args.write_output:
        write_official_reference_record(record, args.write_output)
        payload["written"] = str(Path(args.write_output))

    if args.json:
        print(stable_json_dumps(payload), end="")
    else:
        print(
            f"{payload['script']}: {payload['status']} commit={payload['upstream_commit']} "
            f"model={payload['model_id']} config={payload['config']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
