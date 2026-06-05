#!/usr/bin/env python3
"""Summarize per-game action distributions from bins or JSON-encoded D2E MCAP.

The wrapper consumes a dataset manifest plus exactly one action source:
dependency-light canonical-bin JSON, offline synthetic MCAP-like JSON records,
or real JSON/JSONSchema MCAP files referenced by the dataset manifest. Real
MCAP reading uses the optional ``mcap.reader`` adapter; default tests stay
offline and do not require the package or mounted D2E data.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from fdm_1_with_d2e import __version__
from fdm_1_with_d2e.data import (
    DecodedMcapJsonActions,
    MANIFEST_STORY_ID,
    OptionalOWAMcapDependencyError,
    action_bins_from_jsonable,
    bin_decoded_mcap_json_actions,
    build_action_distribution_manifest,
    decode_d2e_json_mcap_records,
    load_json,
    read_d2e_json_mcap_actions,
    stable_json_dumps,
    stable_manifest_id,
    write_json_artifact,
)

DEFAULT_CONFIG = Path("configs/data/phase0_manifest_builders.json")
JSONDict = dict[str, Any]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Committed builder config to record.")
    parser.add_argument("--dataset-manifest", help="Dataset manifest JSON produced by build_d2e_manifest.py.")
    parser.add_argument("--bins-json", help="JSON mapping recording_id to canonical ActionBin fixture dictionaries.")
    parser.add_argument(
        "--records-json",
        help=(
            "Offline fixture JSON mapping recording_id to synthetic MCAP-like decoded records; "
            "bypasses the optional mcap package."
        ),
    )
    parser.add_argument(
        "--from-mcap-json",
        action="store_true",
        help="Decode JSON/JSONSchema .mcap files referenced by the dataset manifest; requires optional mcap.reader.",
    )
    parser.add_argument(
        "--dataset-root",
        help="Override dataset_manifest.dataset_root when resolving relative mcap_path values and guarding outputs.",
    )
    parser.add_argument(
        "--recording-id",
        action="append",
        default=[],
        help="Restrict real/fixture MCAP decoding to a recording_id; repeatable.",
    )
    parser.add_argument(
        "--max-recordings",
        type=int,
        help="Bound the number of selected recordings for real/fixture MCAP decoding.",
    )
    parser.add_argument(
        "--one-per-game",
        action="store_true",
        help="Select only the first manifest recording for each game before max-recordings is applied.",
    )
    parser.add_argument("--output", help="Optional output path for the action-distribution manifest.")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    source_count = sum(bool(value) for value in (args.bins_json, args.records_json, args.from_mcap_json))
    if args.dataset_manifest is None or source_count == 0:
        payload = {
            "story_id": MANIFEST_STORY_ID,
            "package_version": __version__,
            "script": Path(__file__).name,
            "config": str(config_path),
            "config_exists": config_path.exists(),
            "status": "action_distribution_builder_available",
            "offline_only": True,
            "requires_dataset_manifest_and_bins_json": True,
            "requires_dataset_manifest_and_action_source": True,
            "supports_json_mcap_decode": True,
            "bounded_decode_options": ["--recording-id", "--max-recordings", "--one-per-game"],
        }
        _emit(payload, json_mode=args.json)
        return 0
    if source_count != 1:
        parser.error("provide exactly one action source: --bins-json, --records-json, or --from-mcap-json")

    dataset_manifest = load_json(args.dataset_manifest)
    dataset_root = args.dataset_root or dataset_manifest.get("dataset_root")
    source_summary = None
    if args.bins_json:
        bins_payload = load_json(args.bins_json)
        recording_bins = action_bins_from_jsonable(bins_payload)
    elif args.records_json:
        selected_entries = _select_recording_entries(
            dataset_manifest,
            recording_ids=args.recording_id,
            max_recordings=args.max_recordings,
            one_per_game=args.one_per_game,
        )
        records_payload = load_json(args.records_json)
        recording_bins, source_summary = _recording_bins_from_decoded_records_json(
            selected_entries,
            records_payload,
        )
    else:
        selected_entries = _select_recording_entries(
            dataset_manifest,
            recording_ids=args.recording_id,
            max_recordings=args.max_recordings,
            one_per_game=args.one_per_game,
        )
        try:
            recording_bins, source_summary = _recording_bins_from_real_mcaps(
                selected_entries,
                dataset_root=dataset_root,
            )
        except OptionalOWAMcapDependencyError as exc:
            parser.exit(2, f"{Path(__file__).name}: {exc}\n")
    distribution = build_action_distribution_manifest(dataset_manifest, recording_bins)
    if source_summary is not None:
        distribution = _attach_source_summary(distribution, source_summary)

    written: dict[str, str] = {}
    if args.output:
        written["action_distribution"] = str(
            write_json_artifact(distribution, args.output, dataset_root=dataset_root)
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


def _select_recording_entries(
    dataset_manifest: JSONDict,
    *,
    recording_ids: list[str],
    max_recordings: int | None,
    one_per_game: bool,
) -> list[JSONDict]:
    if max_recordings is not None and max_recordings < 0:
        raise ValueError("--max-recordings must be non-negative")
    entries = [dict(entry) for entry in dataset_manifest.get("recordings", ())]
    if recording_ids:
        requested = set(recording_ids)
        entries = [entry for entry in entries if str(entry.get("recording_id")) in requested]
        missing = sorted(requested - {str(entry.get("recording_id")) for entry in entries})
        if missing:
            raise ValueError(f"--recording-id not found in dataset manifest: {missing}")
    if one_per_game:
        seen_games: set[str] = set()
        selected: list[JSONDict] = []
        for entry in entries:
            game = str(entry.get("game", ""))
            if game in seen_games:
                continue
            selected.append(entry)
            seen_games.add(game)
        entries = selected
    if max_recordings is not None:
        entries = entries[:max_recordings]
    return entries


def _recording_bins_from_decoded_records_json(
    selected_entries: list[JSONDict],
    records_payload: JSONDict,
) -> tuple[dict[str, object], JSONDict]:
    raw_records_by_id = records_payload.get("recording_records", records_payload)
    if not isinstance(raw_records_by_id, dict):
        raise ValueError("--records-json must be a mapping or contain a 'recording_records' mapping")

    recording_bins: dict[str, object] = {}
    summaries: dict[str, JSONDict] = {}
    for entry in selected_entries:
        recording_id = str(entry["recording_id"])
        if recording_id not in raw_records_by_id:
            raise ValueError(f"--records-json missing selected recording_id: {recording_id}")
        decoded = decode_d2e_json_mcap_records(raw_records_by_id[recording_id])
        binned = bin_decoded_mcap_json_actions(decoded)
        recording_bins[recording_id] = binned.bins
        summaries[recording_id] = _decoded_recording_summary(decoded, binned.dropped_event_count, len(binned.bins))
    return recording_bins, _source_summary("decoded_records_json", selected_entries, summaries)


def _recording_bins_from_real_mcaps(
    selected_entries: list[JSONDict],
    *,
    dataset_root: str | Path | None,
) -> tuple[dict[str, object], JSONDict]:
    recording_bins: dict[str, object] = {}
    summaries: dict[str, JSONDict] = {}
    for entry in selected_entries:
        recording_id = str(entry["recording_id"])
        mcap_path = _resolve_mcap_path(entry, dataset_root)
        decoded = read_d2e_json_mcap_actions(mcap_path)
        binned = bin_decoded_mcap_json_actions(decoded)
        recording_bins[recording_id] = binned.bins
        summary = _decoded_recording_summary(decoded, binned.dropped_event_count, len(binned.bins))
        summary["mcap_path"] = mcap_path.as_posix()
        summaries[recording_id] = summary
    return recording_bins, _source_summary("mcap_json", selected_entries, summaries)


def _decoded_recording_summary(
    decoded: DecodedMcapJsonActions,
    dropped_event_count: int,
    bin_count: int,
) -> JSONDict:
    summary = decoded.to_json_summary()
    summary["bin_count"] = bin_count
    summary["dropped_event_count"] = dropped_event_count
    return summary


def _source_summary(source: str, selected_entries: list[JSONDict], summaries: dict[str, JSONDict]) -> JSONDict:
    selected_ids = [str(entry["recording_id"]) for entry in selected_entries]
    return {
        "source": source,
        "selected_recording_count": len(selected_ids),
        "selected_recording_ids": selected_ids,
        "recordings": summaries,
    }


def _attach_source_summary(distribution: JSONDict, source_summary: JSONDict) -> JSONDict:
    payload = dict(distribution)
    payload["source_mcap_json_summary"] = source_summary
    payload["manifest_id"] = ""
    payload["manifest_id"] = stable_manifest_id("action-distribution", payload)
    return payload


def _resolve_mcap_path(entry: JSONDict, dataset_root: str | Path | None) -> Path:
    if "mcap_path" not in entry:
        raise ValueError(f"dataset manifest entry missing mcap_path for {entry.get('recording_id')!r}")
    path = Path(str(entry["mcap_path"]))
    if path.is_absolute():
        return path
    if dataset_root is None:
        raise ValueError("dataset manifest has relative mcap_path values; provide --dataset-root or dataset_root")
    return Path(dataset_root) / path


if __name__ == "__main__":
    raise SystemExit(main())
