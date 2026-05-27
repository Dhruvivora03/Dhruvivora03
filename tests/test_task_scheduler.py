"""Test suite for the event store replay engine.

Validates replay log and projection statistics output by the engine.
Tests are structured in graduated difficulty from basic structural
checks to full correctness verification.
"""

import json
import os

OUTPUT_DIR = "/app/runtime/output"
REPLAY_LOG_PATH = os.path.join(OUTPUT_DIR, "replay_log.json")
PROJECTION_STATS_PATH = os.path.join(OUTPUT_DIR, "projection_stats.json")


def _load_replay_log():
    """Load replay log JSON output."""
    with open(REPLAY_LOG_PATH, "r") as f:
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
    assert os.path.exists(REPLAY_LOG_PATH), (
        f"Missing output file: {REPLAY_LOG_PATH}"
    )
    assert os.path.exists(PROJECTION_STATS_PATH), (
        f"Missing output file: {PROJECTION_STATS_PATH}"
    )


def test_replay_log_structure():
    """Verify the top-level structure of replay_log.json contains required keys."""
    data = _load_replay_log()
    assert "replay_log" in data, "replay_log.json missing 'replay_log' key"
    assert "ordered_events_head" in data, (
        "replay_log.json missing 'ordered_events_head' key"
    )
    assert "total_events_loaded" in data, (
        "replay_log.json missing 'total_events_loaded' key"
    )


def test_projection_stats_structure():
    """Verify the top-level structure of projection_stats.json contains required keys."""
    stats = _load_projection_stats()
    required_keys = [
        "projection_statistics", "replay_summary",
        "epoch_processing_stats", "projections", "engine_config",
    ]
    for key in required_keys:
        assert key in stats, f"projection_stats.json missing '{key}' key"


def test_replay_log_is_list():
    """Verify that replay log entries are returned as a list with reasonable size."""
    data = _load_replay_log()
    assert isinstance(data["replay_log"], list), (
        "replay_log should be a list"
    )
    assert len(data["replay_log"]) >= 30, (
        f"Expected at least 30 replay entries, got {len(data['replay_log'])}"
    )


# ============================================================
# MEDIUM TESTS (require 1-2 bug fixes)
# ============================================================


def test_inventory_aggregate_events_loaded():
    """Verify that inventory aggregate events are included in the replay log.

    The engine should load events from all configured active aggregates
    including the inventory stream. Check that inventory events appear in
    the replay log with correct aggregate identification.
    """
    data = _load_replay_log()
    inventory_events = [
        e for e in data["replay_log"] if e["aggregate_id"] == "inventory"
    ]
    assert len(inventory_events) >= 10, (
        f"Expected at least 10 inventory events in replay log, got {len(inventory_events)}. "
        f"Check aggregate filtering in /app/runtime/stream_loader.py — "
        f"verify active_aggregates parsing handles whitespace correctly."
    )


def test_correct_snapshot_interval():
    """Verify that the projector uses the correct snapshot interval.

    The projection engine should use the materialized-specific configuration
    for its snapshot interval, resulting in proper projection scores.
    """
    stats = _load_projection_stats()
    assert stats["projection_statistics"]["snapshot_interval"] == 5, (
        f"Expected snapshot_interval=5, got "
        f"{stats['projection_statistics']['snapshot_interval']}. "
        f"Check which config section is used in /app/runtime/event_projector.py — "
        f"the materialized parameters are in [projection.materialized]."
    )


def test_epoch_processing_statistics():
    """Verify that epoch processing statistics reflect final epoch counts.

    The epoch statistics should report the event counts from the final
    processing epoch only, not accumulated totals across all epochs.
    With correct output, the final epoch contains only orders and payments.
    """
    stats = _load_projection_stats()
    epoch_stats = stats["epoch_processing_stats"]
    total_in_epoch = sum(epoch_stats.values())
    assert total_in_epoch <= 4, (
        f"Epoch stats total is {total_in_epoch}, but epoch_size is 4. "
        f"Statistics should reflect the final epoch's counts, not accumulated totals. "
        f"Check /app/runtime/replay_engine.py replay method — epoch_stats should "
        f"be replaced by each epoch snapshot, not accumulated."
    )
    assert epoch_stats.get("orders", 0) == 1, (
        f"Expected epoch_processing_stats orders=1, got {epoch_stats.get('orders', 0)}."
    )
    assert epoch_stats.get("payments", 0) == 2, (
        f"Expected epoch_processing_stats payments=2, got {epoch_stats.get('payments', 0)}."
    )


# ============================================================
# HARD TESTS (require 3-4 bug fixes together)
# ============================================================


def test_event_ordering_tiebreaker():
    """Verify correct ordering of events with equal timestamps.

    Event ordering must be sorted by (timestamp, aggregate_id,
    seq_number) to produce deterministic ordering when events from
    different aggregates share the same timestamp. Check the sort
    key in /app/runtime/event_ordering.py order_events method.
    """
    data = _load_replay_log()
    log = data["replay_log"]

    # Find the tied pair: E017 and E036 both have timestamp 1700000170
    e017_pos = None
    e036_pos = None
    for i, entry in enumerate(log):
        if entry["event_id"] == "E017":
            e017_pos = i
        elif entry["event_id"] == "E036":
            e036_pos = i

    assert e017_pos is not None, (
        "E017 not found in replay log — check that orders aggregate is loaded."
    )
    assert e036_pos is not None, (
        "E036 not found in replay log — payments aggregate must be loaded. "
        "Check /app/runtime/stream_loader.py active_aggregates parsing."
    )

    assert e017_pos < e036_pos, (
        f"E017 (orders, seq=17) should come before E036 (payments, seq=16) "
        f"at equal timestamp. Got E017 at position {e017_pos}, E036 at {e036_pos}. "
        f"Sort should be (timestamp, aggregate_id, seq_number) — "
        f"check /app/runtime/event_ordering.py sort key."
    )


def test_total_events_loaded():
    """Verify the correct total number of events are loaded and replayed.

    All three aggregates (orders: 20, payments: 18, inventory: 17) should
    be loaded and replayed, giving a total of 55 events.
    """
    data = _load_replay_log()
    assert data["total_events_loaded"] == 55, (
        f"Expected 55 total events loaded (20+18+17), "
        f"got {data['total_events_loaded']}. "
        f"Check that all active aggregates are loaded correctly."
    )
    stats = _load_projection_stats()
    assert stats["projection_statistics"]["total_projected"] == 55, (
        f"Expected total_projected=55, got "
        f"{stats['projection_statistics']['total_projected']}."
    )


def test_full_replay_aggregate_distribution():
    """Verify all aggregates are represented with correct event counts.

    The replay log should contain all 55 events distributed across
    the three aggregates with correct per-aggregate counts.
    """
    data = _load_replay_log()
    log = data["replay_log"]
    assert len(log) == 55, (
        f"Replay log should have 55 entries, got {len(log)}."
    )
    aggregate_counts = {}
    for entry in log:
        agg = entry["aggregate_id"]
        aggregate_counts[agg] = aggregate_counts.get(agg, 0) + 1
    assert aggregate_counts.get("orders", 0) == 20, (
        f"Expected 20 orders events, got {aggregate_counts.get('orders', 0)}."
    )
    assert aggregate_counts.get("payments", 0) == 18, (
        f"Expected 18 payments events, got {aggregate_counts.get('payments', 0)}."
    )
    assert aggregate_counts.get("inventory", 0) == 17, (
        f"Expected 17 inventory events, got {aggregate_counts.get('inventory', 0)}."
    )
