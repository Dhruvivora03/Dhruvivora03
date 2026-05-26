"""Test suite for the event sourcing ledger replay engine.

Validates ledger results and projection statistics output by the engine.
Tests are structured in graduated difficulty from basic structural
checks to full correctness verification.
"""

import json
import os

OUTPUT_DIR = "/app/runtime/output"
LEDGER_RESULTS_PATH = os.path.join(OUTPUT_DIR, "ledger_results.json")
PROJECTION_STATS_PATH = os.path.join(OUTPUT_DIR, "projection_stats.json")


def _load_ledger_results():
    """Load ledger results JSON output."""
    with open(LEDGER_RESULTS_PATH, "r") as f:
        return json.load(f)


def _load_projection_stats():
    """Load projection statistics JSON output."""
    with open(PROJECTION_STATS_PATH, "r") as f:
        return json.load(f)


# ============================================================
# EASY TESTS (pass even with buggy code)
# ============================================================


def test_output_files_exist():
    """Verify that the engine produces both expected output files."""
    assert os.path.exists(LEDGER_RESULTS_PATH), (
        f"Missing output file: {LEDGER_RESULTS_PATH}"
    )
    assert os.path.exists(PROJECTION_STATS_PATH), (
        f"Missing output file: {PROJECTION_STATS_PATH}"
    )


def test_ledger_results_structure():
    """Verify the top-level structure of ledger_results.json contains required keys."""
    data = _load_ledger_results()
    assert "event_order" in data, "ledger_results.json missing 'event_order' key"
    assert "account_summaries" in data, (
        "ledger_results.json missing 'account_summaries' key"
    )
    assert "total_events_replayed" in data, (
        "ledger_results.json missing 'total_events_replayed' key"
    )
    assert "event_counts_by_stream" in data, (
        "ledger_results.json missing 'event_counts_by_stream' key"
    )


def test_projection_stats_structure():
    """Verify the top-level structure of projection_stats.json contains required keys."""
    stats = _load_projection_stats()
    required_keys = [
        "window_projections", "total_events",
        "streams_processed", "accounts_active",
    ]
    for key in required_keys:
        assert key in stats, f"projection_stats.json missing '{key}' key"


def test_account_summaries_are_list():
    """Verify that account summaries are returned as a list with expected accounts."""
    data = _load_ledger_results()
    assert isinstance(data["account_summaries"], list), (
        "account_summaries should be a list"
    )
    assert len(data["account_summaries"]) == 7, (
        f"Expected 7 account summaries, got {len(data['account_summaries'])}"
    )


# ============================================================
# MEDIUM TESTS (require 1-2 bug fixes)
# ============================================================


def test_adjustment_stream_events_present():
    """Verify that adjustment stream events are included in the replay.

    The engine should replay events from all configured active streams
    including the adjustments stream. Check that adjustment events
    appear in the event counts.
    """
    data = _load_ledger_results()
    counts = data["event_counts_by_stream"]
    assert counts.get("adjustments", 0) >= 15, (
        f"Expected at least 15 adjustment events, got {counts.get('adjustments', 0)}. "
        f"Check stream filtering in /app/runtime/event_loader.py — "
        f"verify active_streams parsing handles whitespace correctly."
    )


def test_correct_window_size_effect():
    """Verify that the replay engine uses the correct window size from config.

    The projection output should reflect processing with the streaming-specific
    window size, not the generic replay window size. With correct window size
    of 10, the projections should differ from raw account balances.
    """
    data = _load_ledger_results()
    stats = _load_projection_stats()
    # With correct window_size=10, projections represent last-window balances
    # which should NOT equal the full account balances (unlike window_size=30+)
    acc100_balance = None
    for s in data["account_summaries"]:
        if s["account_id"] == "ACC100":
            acc100_balance = s["final_balance"]
            break
    acc100_projection = stats["window_projections"].get("ACC100")
    assert acc100_projection is not None, (
        "window_projections missing ACC100. "
        "Check /app/runtime/ledger_engine.py — verify which config section "
        "provides the window_size parameter. Use [replay.streaming] section."
    )
    assert acc100_projection != acc100_balance, (
        f"ACC100 projection ({acc100_projection}) equals full balance "
        f"({acc100_balance}). Window projections should reflect the final "
        f"window only, not accumulated totals. Check window_size config section "
        f"in /app/runtime/ledger_engine.py."
    )


def test_window_projection_values():
    """Verify that window projections reflect per-window counts correctly.

    The projections should report the account balances from the final
    processing window only, not accumulated totals across all windows.
    """
    stats = _load_projection_stats()
    projections = stats["window_projections"]
    assert projections.get("ACC101") == 420.0, (
        f"Expected window_projections['ACC101']=420.0, got {projections.get('ACC101')}. "
        f"Projections should reflect the final window's balances, not accumulated totals. "
        f"Check /app/runtime/ledger_engine.py compute_window_projections method."
    )
    assert projections.get("ACC106") == 110.0, (
        f"Expected window_projections['ACC106']=110.0, got {projections.get('ACC106')}."
    )
    assert projections.get("ACC105") == 158.0, (
        f"Expected window_projections['ACC105']=158.0, got {projections.get('ACC105')}."
    )


# ============================================================
# HARD TESTS (require 3-4 bug fixes together)
# ============================================================


def test_event_ordering_at_same_timestamp():
    """Verify correct ordering of events sharing the same timestamp.

    Events at timestamp 1700001500 must be sorted by (timestamp, stream_id, seq)
    to produce deterministic ordering. The correct order is:
    ADJ012 (adjustments), PAY015 (payments), REF015 (refunds).
    Check the sort key in /app/runtime/ledger_engine.py sort_events method.
    """
    data = _load_ledger_results()
    event_order = data["event_order"]

    # Find events at timestamp 1700001500
    ts_events = [e for e in event_order if e["timestamp"] == 1700001500]
    assert len(ts_events) == 3, (
        f"Expected 3 events at timestamp 1700001500, got {len(ts_events)}. "
        f"All streams (including adjustments) must be loaded."
    )

    # Correct order: adjustments < payments < refunds (alphabetical stream_id)
    assert ts_events[0]["event_id"] == "ADJ012", (
        f"First event at timestamp 1700001500 should be ADJ012 (adjustments "
        f"stream comes before payments alphabetically), got {ts_events[0]['event_id']}. "
        f"Check sort key includes stream_id in /app/runtime/ledger_engine.py — "
        f"sort should be (timestamp, stream_id, seq)."
    )
    assert ts_events[1]["event_id"] == "PAY015", (
        f"Second event at timestamp 1700001500 should be PAY015, "
        f"got {ts_events[1]['event_id']}."
    )
    assert ts_events[2]["event_id"] == "REF015", (
        f"Third event at timestamp 1700001500 should be REF015, "
        f"got {ts_events[2]['event_id']}."
    )


def test_total_events_replayed():
    """Verify the correct total number of events are replayed.

    All three streams (payments: 20, refunds: 18, adjustments: 17) should
    be loaded and replayed, giving a total of 55 events.
    """
    data = _load_ledger_results()
    assert data["total_events_replayed"] == 55, (
        f"Expected 55 total events replayed (20+18+17), "
        f"got {data['total_events_replayed']}. "
        f"Check that all active streams are loaded correctly."
    )
    stats = _load_projection_stats()
    assert stats["total_events"] == 55, (
        f"Expected total_events=55, got {stats['total_events']}."
    )
    assert "adjustments" in stats["streams_processed"], (
        "streams_processed should include 'adjustments'."
    )


def test_full_account_balance_accuracy():
    """Verify account balances are computed correctly with all streams included.

    With all 55 events replayed, account balances should reflect payments,
    refunds, and adjustments combined.
    """
    data = _load_ledger_results()
    balances = {s["account_id"]: s["final_balance"]
                for s in data["account_summaries"]}
    assert balances.get("ACC100") == 668.75, (
        f"Expected ACC100 balance=668.75, got {balances.get('ACC100')}. "
        f"Balance must include adjustment events."
    )
    assert balances.get("ACC101") == 718.25, (
        f"Expected ACC101 balance=718.25, got {balances.get('ACC101')}."
    )
    assert balances.get("ACC102") == 552.0, (
        f"Expected ACC102 balance=552.0, got {balances.get('ACC102')}."
    )
    assert balances.get("ACC103") == 803.0, (
        f"Expected ACC103 balance=803.0, got {balances.get('ACC103')}."
    )
