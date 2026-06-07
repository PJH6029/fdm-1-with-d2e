from __future__ import annotations

from fdm_1_with_d2e.data import ActionBin, KeyboardEvent, KeyboardEventType, MouseButton, MouseButtonEvent, MouseButtonEventType, ScrollEvent, ns_from_ms
from fdm_1_with_d2e.reporting.overflow_stats import aggregate_recording_summaries, sparse_candidate_tokens, summarize_overflow_for_bins


def test_sparse_candidate_tokens_counts_scroll_directions_separately() -> None:
    action_bin = ActionBin(
        0,
        0,
        ns_from_ms(50),
        keyboard_events=(KeyboardEvent(ns_from_ms(1), "A", KeyboardEventType.DOWN),),
        mouse_button_events=(MouseButtonEvent(ns_from_ms(2), MouseButton.RIGHT, MouseButtonEventType.UP),),
        scroll_events=(ScrollEvent(ns_from_ms(3), delta_x=-1, delta_y=1),),
    )

    assert sparse_candidate_tokens(action_bin) == (
        "KEY_DOWN_A",
        "MOUSE_RIGHT_UP",
        "SCROLL_UP",
        "SCROLL_LEFT",
    )


def test_summarize_overflow_for_bins_reports_k_sweep_and_dropped_families() -> None:
    bins = (
        ActionBin(0, 0, ns_from_ms(50), keyboard_events=(KeyboardEvent(ns_from_ms(1), "A", KeyboardEventType.DOWN),)),
        ActionBin(
            1,
            ns_from_ms(50),
            ns_from_ms(100),
            keyboard_events=(
                KeyboardEvent(ns_from_ms(51), "A", KeyboardEventType.DOWN),
                KeyboardEvent(ns_from_ms(52), "B", KeyboardEventType.DOWN),
                KeyboardEvent(ns_from_ms(53), "A", KeyboardEventType.UP),
            ),
            mouse_button_events=(MouseButtonEvent(ns_from_ms(54), MouseButton.LEFT, MouseButtonEventType.DOWN),),
            scroll_events=(ScrollEvent(ns_from_ms(55), delta_y=-1),),
        ),
    )

    summary = summarize_overflow_for_bins(
        recording_id="rec",
        game="game",
        bins=bins,
        slots_per_bin=3,
        k_sweep=(2, 3, 8),
    )

    assert summary["bin_count"] == 2
    assert summary["overflow_bin_count"] == 1
    assert summary["max_sparse_candidate_tokens_per_bin"] == 5
    assert summary["candidate_token_count_histogram"] == {"1": 1, "5": 1}
    assert summary["k_sweep"]["2"]["overflow_bin_count"] == 1
    assert summary["k_sweep"]["8"]["overflow_bin_count"] == 0
    assert summary["dropped_token_family_counts_in_overflow_bins_at_default_k"]
    assert summary["overflow_examples"][0]["candidate_token_count"] == 5


def test_aggregate_recording_summaries_combines_games_and_histograms() -> None:
    first = summarize_overflow_for_bins(
        recording_id="a",
        game="g1",
        bins=(ActionBin(0, 0, ns_from_ms(50)),),
        slots_per_bin=1,
        k_sweep=(1, 2),
    )
    second = summarize_overflow_for_bins(
        recording_id="b",
        game="g1",
        bins=(ActionBin(0, 0, ns_from_ms(50), keyboard_events=(KeyboardEvent(ns_from_ms(1), "A", KeyboardEventType.DOWN), KeyboardEvent(ns_from_ms(2), "B", KeyboardEventType.DOWN))),),
        slots_per_bin=1,
        k_sweep=(1, 2),
    )

    aggregate = aggregate_recording_summaries([first, second], slots_per_bin=1, k_sweep=(1, 2))

    assert aggregate["recording_count"] == 2
    assert aggregate["bin_count"] == 2
    assert aggregate["overflow_bin_count"] == 1
    assert aggregate["k_sweep"]["1"]["overflow_bin_count"] == 1
    assert aggregate["k_sweep"]["2"]["overflow_bin_count"] == 0
    assert aggregate["per_game"]["g1"]["recording_count"] == 2
