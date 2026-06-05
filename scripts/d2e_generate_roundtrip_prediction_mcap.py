#!/usr/bin/env python3
"""Generate an official-evaluator-readable prediction MCAP through OWA writer APIs.

With no source/output arguments this wrapper emits an offline availability record.
Actual MCAP generation requires the optional pinned D2E/OWA runtime dependencies
(``mcap_owa`` and ``owa.msgs``) and is intended for MLXP/real-D2E smoke runs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from fdm_1_with_d2e import __version__
from fdm_1_with_d2e.evaluation import (
    OFFICIAL_ROUNDTRIP_ACTION_MODES,
    OFFICIAL_ROUNDTRIP_GENERATED_BY,
    OFFICIAL_ROUNDTRIP_REQUIRED_TOPICS,
    OFFICIAL_ROUNDTRIP_STORY_ID,
    OptionalOfficialMcapDependencyError,
    default_provenance_json_path,
    generate_writer_roundtrip_prediction_mcap,
    stable_json_dumps,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-mcap", help="Real D2E ground-truth/source MCAP to read.")
    parser.add_argument("--prediction-mcap", help="Output prediction MCAP to create through OWAMcapWriter.")
    parser.add_argument(
        "--action-mode",
        choices=OFFICIAL_ROUNDTRIP_ACTION_MODES,
        default="exact",
        help=(
            "'exact' re-emits decoded OWA actions for schema sanity; 'tokenized' routes actions "
            "through this repo's decoder, 50ms binner, tokenizer, de-tokenizer, and OWA writer."
        ),
    )
    parser.add_argument(
        "--provenance-json",
        help="Sidecar provenance JSON path. Defaults to '<prediction-mcap>.provenance.json' when generating.",
    )
    parser.add_argument("--dataset-root", help="Read-only D2E dataset root used to guard output paths.")
    parser.add_argument(
        "--max-duration-seconds",
        type=float,
        help="Optional positive duration bound from the first screen event. Omit to emit the full source span.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing prediction/provenance output.")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    args = parser.parse_args(argv)

    if args.source_mcap is None and args.prediction_mcap is None:
        payload = {
            "story_id": OFFICIAL_ROUNDTRIP_STORY_ID,
            "package_version": __version__,
            "script": Path(__file__).name,
            "status": "official_writer_roundtrip_cli_available",
            "offline_only": True,
            "requires_source_mcap_and_prediction_mcap": True,
            "requires_optional_owa_dependencies_for_generation": True,
            "action_modes": list(OFFICIAL_ROUNDTRIP_ACTION_MODES),
            "required_topics": list(OFFICIAL_ROUNDTRIP_REQUIRED_TOPICS),
            "generated_by": OFFICIAL_ROUNDTRIP_GENERATED_BY,
        }
        _emit(payload, json_mode=args.json)
        return 0
    if args.source_mcap is None or args.prediction_mcap is None:
        parser.error("--source-mcap and --prediction-mcap must be provided together")

    prediction_path = Path(args.prediction_mcap)
    provenance_path = Path(args.provenance_json) if args.provenance_json else default_provenance_json_path(prediction_path)
    if provenance_path.exists() and not args.overwrite:
        parser.error(f"provenance JSON already exists; pass --overwrite: {provenance_path}")

    try:
        provenance = generate_writer_roundtrip_prediction_mcap(
            args.source_mcap,
            prediction_path,
            action_mode=args.action_mode,
            provenance_json_path=provenance_path,
            dataset_root=args.dataset_root,
            max_duration_seconds=args.max_duration_seconds,
            overwrite=args.overwrite,
        )
    except (OptionalOfficialMcapDependencyError, ImportError) as exc:
        parser.exit(2, f"{Path(__file__).name}: {exc}\n")

    payload = {"status": "official_writer_roundtrip_prediction_mcap_generated", "provenance": provenance}
    if args.json:
        print(stable_json_dumps(payload), end="")
    else:
        print(
            f"{Path(__file__).name}: {payload['status']} "
            f"prediction={prediction_path} provenance={provenance_path}"
        )
    return 0


def _emit(payload: dict[str, object], *, json_mode: bool) -> None:
    if json_mode:
        print(stable_json_dumps(payload), end="")
    else:
        print(f"{payload['script']}: {payload['status']}")


if __name__ == "__main__":
    raise SystemExit(main())
