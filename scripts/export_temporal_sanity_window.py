#!/usr/bin/env python3
"""Export a 10s per-bin D2E temporal sanity window with frames and tokens."""

from __future__ import annotations

import argparse
from pathlib import Path

from fdm_1_with_d2e import __version__
from fdm_1_with_d2e.data import stable_json_dumps
from fdm_1_with_d2e.reporting.temporal_sanity import availability_payload, export_temporal_sanity_window


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", help="Real D2E .mkv path used for frame PNG export.")
    parser.add_argument("--mcap", help="Real D2E .mcap path to decode.")
    parser.add_argument("--output-dir", help="Output artifact directory outside the dataset tree.")
    parser.add_argument("--dataset-root", help="Read-only dataset root used to guard output paths.")
    parser.add_argument("--duration-seconds", type=float, default=10.0)
    parser.add_argument("--start-bin", type=int, help="Optional explicit 50ms bin index in the binned screen span.")
    parser.add_argument("--start-seconds", type=float, help="Optional explicit start offset from screen-span start.")
    parser.add_argument("--no-frames", action="store_true", help="Write JSON artifacts only; do not require OpenCV/video.")
    parser.add_argument("--no-frame-overlay", action="store_true", help="Write raw frames without action text overlay.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.video is None and args.mcap is None and args.output_dir is None:
        payload = {**availability_payload(), "package_version": __version__, "script": Path(__file__).name}
        print(stable_json_dumps(payload), end="" if args.json else "\n")
        return 0
    if args.mcap is None or args.output_dir is None:
        parser.error("--mcap and --output-dir are required for export")
    if not args.no_frames and args.video is None:
        parser.error("--video is required unless --no-frames is set")

    summary = export_temporal_sanity_window(
        video_path=args.video,
        mcap_path=args.mcap,
        output_dir=args.output_dir,
        dataset_root=args.dataset_root,
        duration_seconds=args.duration_seconds,
        start_bin=args.start_bin,
        start_seconds=args.start_seconds,
        write_frames=not args.no_frames,
        frame_overlay=not args.no_frame_overlay,
    )
    payload = {"status": "temporal_sanity_window_exported", "summary": summary}
    if args.json:
        print(stable_json_dumps(payload), end="")
    else:
        print(
            f"{Path(__file__).name}: {payload['status']} "
            f"bins={summary['selection']['length_bins']} out={summary['output_dir']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
