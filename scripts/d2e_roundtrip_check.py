#!/usr/bin/env python3
"""Run an offline D2E-style fixture round-trip check.

The default path constructs canonical 50ms bins, tokenizes/de-tokenizes them,
reconstructs writer-compatible event dictionaries, and evaluates local D2E-style
metrics. It performs no D2E, Hugging Face, MLXP, MCAP, or network I/O.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from fdm_1_with_d2e import __version__
from fdm_1_with_d2e.data import ActionBin, KeyboardEvent, KeyboardEventType, MouseButton, MouseButtonEvent, MouseButtonEventType
from fdm_1_with_d2e.evaluation import (
    EVALUATOR_STORY_ID,
    compute_d2e_primary_metrics,
    metric_values,
    stable_json_dumps,
    tokenized_bins_to_writer_records,
)
from fdm_1_with_d2e.tokenization import DEFAULT_ACTION_TOKENIZER, DEFAULT_ACTION_VOCAB, tokenize_action_bins

DEFAULT_CONFIG = Path("configs/evaluation/d2e_local.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Committed local evaluation config to record.")
    parser.add_argument("--json", action="store_true", help="Emit JSON fixture evidence to stdout.")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    ground_truth_bins = _fixture_bins()
    tokenized = tokenize_action_bins(ground_truth_bins, tokenizer=DEFAULT_ACTION_TOKENIZER)
    predicted_bins = DEFAULT_ACTION_TOKENIZER.detokenize_bins(tokenized)
    writer_records = tokenized_bins_to_writer_records(tokenized, tokenizer=DEFAULT_ACTION_TOKENIZER)
    metrics = compute_d2e_primary_metrics(
        ground_truth_bins,
        predicted_bins,
        group={"fixture": "representative-token-roundtrip"},
    )
    compact_values = metric_values(metrics)
    expected_perfect = len(compact_values) == 6 and all(value == 1.0 for value in compact_values.values())
    status = "fixture_roundtrip_passed" if expected_perfect else "fixture_roundtrip_failed"

    payload = {
        "story_id": EVALUATOR_STORY_ID,
        "package_version": __version__,
        "script": Path(__file__).name,
        "config": str(config_path),
        "config_exists": config_path.exists(),
        "status": status,
        "offline_only": True,
        "fixture": {
            "bin_count": len(ground_truth_bins),
            "tokens_per_bin": DEFAULT_ACTION_TOKENIZER.tokens_per_bin,
            "token_count": len(tokenized.tokens),
            "writer_record_count": len(writer_records),
            "overflow_bin_count": tokenized.overflow_bin_count,
        },
        "metric_values": compact_values,
        "metrics": metrics,
    }

    if args.json:
        print(stable_json_dumps(payload), end="")
    else:
        print(
            f"{payload['script']}: {payload['status']} bins={len(ground_truth_bins)} "
            f"writer_records={len(writer_records)} config={payload['config']}"
        )
    return 0 if expected_perfect else 1


def _fixture_bins() -> tuple[ActionBin, ...]:
    """Return bins whose mouse deltas are exactly representable by the default tokenizer."""

    zero = DEFAULT_ACTION_VOCAB.mouse_quantizer.zero_bin_index
    dx_pos, dy_zero = DEFAULT_ACTION_VOCAB.mouse_quantizer.dequantize_token(f"MOUSE_MOVE_BIN_{zero + 1}_{zero}")
    dx_neg, dy_pos = DEFAULT_ACTION_VOCAB.mouse_quantizer.dequantize_token(f"MOUSE_MOVE_BIN_{zero - 1}_{zero + 1}")
    dx_big, dy_neg = DEFAULT_ACTION_VOCAB.mouse_quantizer.dequantize_token(f"MOUSE_MOVE_BIN_{zero + 2}_{zero - 1}")
    width = 50_000_000
    return (
        ActionBin(
            index=0,
            start_ns=0,
            end_ns=width,
            mouse_dx=0,
            mouse_dy=0,
            keyboard_events=(KeyboardEvent(timestamp_ns=10_000_000, key="KEY_A", event_type=KeyboardEventType.DOWN),),
            mouse_button_events=(
                MouseButtonEvent(timestamp_ns=20_000_000, button=MouseButton.LEFT, event_type=MouseButtonEventType.DOWN),
            ),
        ),
        ActionBin(index=1, start_ns=width, end_ns=2 * width, mouse_dx=dx_pos, mouse_dy=dy_zero),
        ActionBin(
            index=2,
            start_ns=2 * width,
            end_ns=3 * width,
            mouse_dx=dx_neg,
            mouse_dy=dy_pos,
            keyboard_events=(KeyboardEvent(timestamp_ns=110_000_000, key="KEY_A", event_type=KeyboardEventType.UP),),
            mouse_button_events=(
                MouseButtonEvent(timestamp_ns=120_000_000, button=MouseButton.LEFT, event_type=MouseButtonEventType.UP),
                MouseButtonEvent(timestamp_ns=125_000_000, button=MouseButton.RIGHT, event_type=MouseButtonEventType.DOWN),
            ),
        ),
        ActionBin(
            index=3,
            start_ns=3 * width,
            end_ns=4 * width,
            mouse_dx=dx_big,
            mouse_dy=dy_neg,
            mouse_button_events=(
                MouseButtonEvent(timestamp_ns=170_000_000, button=MouseButton.RIGHT, event_type=MouseButtonEventType.UP),
            ),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
