from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fdm_1_with_d2e.data import ActionBin, KeyboardEvent, KeyboardEventType, MouseButton, MouseButtonEvent, MouseButtonEventType
from fdm_1_with_d2e.evaluation import MOUSE_BUTTON_ACCURACY, compute_d2e_primary_metrics, metric_values, tokenized_bins_to_writer_records
from fdm_1_with_d2e.tokenization import DEFAULT_ACTION_TOKENIZER, DEFAULT_ACTION_VOCAB, tokenize_action_bins

REPO_ROOT = Path(__file__).resolve().parents[3]
WIDTH = 50_000_000


def _representable_fixture_bins() -> tuple[ActionBin, ...]:
    zero = DEFAULT_ACTION_VOCAB.mouse_quantizer.zero_bin_index
    dx_pos, dy_pos = DEFAULT_ACTION_VOCAB.mouse_quantizer.dequantize_token(f"MOUSE_MOVE_BIN_{zero + 1}_{zero + 1}")
    dx_neg, dy_neg = DEFAULT_ACTION_VOCAB.mouse_quantizer.dequantize_token(f"MOUSE_MOVE_BIN_{zero - 1}_{zero - 1}")
    return (
        ActionBin(
            index=0,
            start_ns=0,
            end_ns=WIDTH,
            mouse_dx=dx_neg,
            mouse_dy=dy_neg,
            keyboard_events=(KeyboardEvent(timestamp_ns=1_000_000, key="KEY_A", event_type=KeyboardEventType.DOWN),),
        ),
        ActionBin(
            index=1,
            start_ns=WIDTH,
            end_ns=2 * WIDTH,
            mouse_dx=0,
            mouse_dy=0,
            mouse_button_events=(
                MouseButtonEvent(timestamp_ns=WIDTH + 1_000_000, button=MouseButton.LEFT, event_type=MouseButtonEventType.DOWN),
            ),
        ),
        ActionBin(
            index=2,
            start_ns=2 * WIDTH,
            end_ns=3 * WIDTH,
            mouse_dx=dx_pos,
            mouse_dy=dy_pos,
            keyboard_events=(KeyboardEvent(timestamp_ns=2 * WIDTH + 1_000_000, key="KEY_A", event_type=KeyboardEventType.UP),),
            mouse_button_events=(
                MouseButtonEvent(timestamp_ns=2 * WIDTH + 2_000_000, button=MouseButton.LEFT, event_type=MouseButtonEventType.UP),
            ),
        ),
    )


def test_tokenized_roundtrip_feeds_local_d2e_metrics_and_writer_records() -> None:
    ground_truth = _representable_fixture_bins()
    tokenized = tokenize_action_bins(ground_truth, tokenizer=DEFAULT_ACTION_TOKENIZER)
    predicted = DEFAULT_ACTION_TOKENIZER.detokenize_bins(tokenized)
    writer_records = tokenized_bins_to_writer_records(tokenized)

    values = metric_values(compute_d2e_primary_metrics(ground_truth, predicted))

    assert all(value == 1.0 for value in values.values() if value is not None)
    assert values[MOUSE_BUTTON_ACCURACY] == 1.0
    assert tokenized.overflow_bin_count == 0
    assert {record["topic"] for record in writer_records} == {"keyboard", "mouse_move", "mouse_button"}


def test_roundtrip_cli_runs_offline_fixture_metrics() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/d2e_roundtrip_check.py"), "--json"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    payload = json.loads(result.stdout)

    assert payload["status"] == "fixture_roundtrip_passed"
    assert payload["offline_only"] is True
    assert payload["fixture"]["bin_count"] == 4
    assert payload["metric_values"]["mouse_button_accuracy"] == 1.0
    assert result.stderr == ""


def test_locate_reference_cli_emits_pinned_official_record_without_network() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/locate_d2e_reference.py"), "--json"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    payload = json.loads(result.stdout)

    assert payload["status"] == "official_reference_record_available"
    assert payload["offline_only"] is True
    assert payload["upstream_commit"] == "80e98e26e4dc584ec76fec5789b4a97c275dd032"
    assert payload["record"]["model_id"] == "open-world-agents/Generalist-IDM-1B"
    assert payload["rendered_commands"]["evaluate"].startswith("uv run evaluate.py")
    assert result.stderr == ""


def test_official_roundtrip_writer_cli_reports_offline_availability_without_owa_deps() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/d2e_generate_roundtrip_prediction_mcap.py"), "--json"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    payload = json.loads(result.stdout)

    assert payload["status"] == "official_writer_roundtrip_cli_available"
    assert payload["offline_only"] is True
    assert payload["requires_optional_owa_dependencies_for_generation"] is True
    assert payload["action_modes"] == ["exact", "tokenized"]
    assert payload["required_topics"] == ["screen", "keyboard", "mouse/raw"]
    assert result.stderr == ""
