"""Test suite for the event store replay engine.

Validates projection results and store statistics output by the engine.
Tests are structured in graduated difficulty from basic structural
checks to full correctness verification requiring all bugs to be fixed.
"""

import json
import os

OUTPUT_DIR = "/app/runtime/output"
PROJECTION_RESULTS_PATH = os.path.join(OUTPUT_DIR, "projection_results.json")
STORE_STATS_PATH = os.path.join(OUTPUT_DIR, "store_stats.json")


def _load_projection_results():
    """Load projection results JSON output."""
    with open(PROJECTION_RESULTS_PATH, "r") as f:
        return json.load(f)


def _load_store_stats():
    """Load store statistics JSON output."""
    with open(STORE_STATS_PATH, "r") as f:
        return json.load(f)


# ============================================================
# EASY TESTS (pass even with buggy code)
# ============================================================


def test_output_files_exist():
    """Verify that the engine produces both expected output files."""
    assert os.path.exists(PROJECTION_RESULTS_PATH), (
        f"Missing output file: {PROJECTION_RESULTS_PATH}"
    )
    assert os.path.exists(STORE_STATS_PATH), (
        f"Missing output file: {STORE_STATS_PATH}"
    )


def test_projection_results_structure():
    """Verify the top-level structure of projection_results.json contains required keys."""
    data = _load_projection_results()
    assert "replay_sequence" in data, (
        "projection_results.json missing 'replay_sequence' key"
    )
    assert "projections" in data, (
        "projection_results.json missing 'projections' key"
    )
    assert "total_events_replayed" in data, (
        "projection_results.json missing 'total_events_replayed' key"
    )


def test_store_stats_structure():
    """Verify the top-level structure of store_stats.json contains required keys."""
    stats = _load_store_stats()
    required_keys = [
        "total_events", "snapshot_interval", "snapshots_created",
        "stream_counts", "window_aggregates", "replay_checksum",
    ]
    for key in required_keys:
        assert key in stats, f"store_stats.json missing '{key}' key"


def test_projections_are_list():
    """Verify that projections are returned as a list of entity objects."""
    data = _load_projection_results()
    assert isinstance(data["projections"], list), (
        "projections should be a list"
    )
    assert len(data["projections"]) == 8, (
        f"Expected 8 entity projections, got {len(data['projections'])}"
    )


# ============================================================
# MEDIUM TESTS (require 1-2 bug fixes)
# ============================================================


def test_inventory_stream_loaded():
    """Verify that inventory stream events are included in the event store.

    The engine should load events from all configured active streams
    including the inventory stream. Check that inventory events appear
    in the replay sequence and stream counts.
    """
    stats = _load_store_stats()
    stream_counts = stats["stream_counts"]
    assert "inventory" in stream_counts, (
        f"stream_counts missing 'inventory' — "
        f"check stream name parsing in /app/runtime/stream_loader.py. "
        f"Verify active_streams configuration handles whitespace correctly."
    )
    assert stream_counts["inventory"] == 16, (
        f"Expected 16 inventory events, got {stream_counts['inventory']}."
    )


def test_correct_snapshot_interval():
    """Verify that the event store uses the correct snapshot interval.

    The store should use the incremental projection configuration for
    its snapshot interval parameter, resulting in proper snapshot creation.
    """
    stats = _load_store_stats()
    assert stats["snapshot_interval"] == 10, (
        f"Expected snapshot_interval=10, got {stats['snapshot_interval']}. "
        f"Check which config section is used in /app/runtime/event_store.py — "
        f"the incremental projection parameters are in [projection.incremental]."
    )
    assert stats["snapshots_created"] == 5, (
        f"Expected 5 snapshots (at events 10,20,30,40,50), "
        f"got {stats['snapshots_created']}."
    )


def test_window_aggregate_values():
    """Verify that window aggregates reflect per-window counts correctly.

    The window aggregates should report the event counts from the final
    processing window, not accumulated totals across all windows.
    """
    stats = _load_store_stats()
    aggregates = stats["window_aggregates"]
    assert "inventory" in aggregates, (
        f"window_aggregates missing 'inventory' stream — "
        f"inventory events must be loaded first (check stream loading)."
    )
    assert aggregates["orders"] == 4, (
        f"Expected window_aggregates['orders']=4, got {aggregates.get('orders')}. "
        f"Aggregates should reflect the final window's counts, not accumulated totals. "
        f"Check /app/runtime/projection_engine.py compute_window_aggregates method."
    )
    assert aggregates["payments"] == 5, (
        f"Expected window_aggregates['payments']=5, got {aggregates.get('payments')}."
    )
    assert aggregates["inventory"] == 7, (
        f"Expected window_aggregates['inventory']=7, got {aggregates.get('inventory')}."
    )


# ============================================================
# HARD TESTS (require 3-4 bug fixes together)
# ============================================================


def test_replay_ordering_at_timestamp_tie():
    """Verify correct ordering of events at identical timestamps.

    When multiple streams have events at the same timestamp, the replay
    sequence must sort by (timestamp, stream_id, sequence_number) to
    produce deterministic ordering. Check the sort key in
    /app/runtime/event_store.py get_replay_sequence method.
    """
    data = _load_projection_results()
    sequence = data["replay_sequence"]

    # Find events at timestamp 1700001900 (three events from different streams)
    events_at_ts = [e for e in sequence if e["timestamp"] == 1700001900]
    assert len(events_at_ts) == 3, (
        f"Expected 3 events at timestamp 1700001900, got {len(events_at_ts)}. "
        f"Inventory stream must be loaded — check /app/runtime/stream_loader.py."
    )

    # Correct order: inventory (INV010) < orders (ORD019) < payments (PAY015)
    assert events_at_ts[0]["event_id"] == "INV010", (
        f"First event at ts=1700001900 should be INV010 (inventory), "
        f"got {events_at_ts[0]['event_id']}. "
        f"Check sort key includes stream_id in /app/runtime/event_store.py — "
        f"sort should be (timestamp, stream_id, sequence_number)."
    )
    assert events_at_ts[1]["event_id"] == "ORD019", (
        f"Second event at ts=1700001900 should be ORD019 (orders), "
        f"got {events_at_ts[1]['event_id']}."
    )
    assert events_at_ts[2]["event_id"] == "PAY015", (
        f"Third event at ts=1700001900 should be PAY015 (payments), "
        f"got {events_at_ts[2]['event_id']}."
    )


def test_total_events_stored():
    """Verify the correct total number of events are stored.

    All three streams (orders: 22, payments: 18, inventory: 16) should
    be loaded and stored, giving a total of 56 events.
    """
    data = _load_projection_results()
    assert data["total_events_replayed"] == 56, (
        f"Expected 56 total events replayed (22+18+16), "
        f"got {data['total_events_replayed']}. "
        f"Check that all active streams are loaded correctly."
    )
    stats = _load_store_stats()
    assert stats["total_events"] == 56, (
        f"Expected total_events=56, got {stats['total_events']}."
    )


def test_replay_checksum_deterministic():
    """Verify the replay sequence produces the correct deterministic checksum.

    The MD5 checksum of the event ID sequence validates that all events
    are present and in the correct deterministic order. This requires
    all streams loaded, correct snapshot behavior, and proper sort ordering.
    """
    stats = _load_store_stats()
    expected_checksum = "e0f2923be9e8eb8510e7493d6e9e335c"
    assert stats["replay_checksum"] == expected_checksum, (
        f"Replay checksum mismatch. Expected {expected_checksum}, "
        f"got {stats['replay_checksum']}. This indicates the replay "
        f"sequence order is incorrect — verify all streams are loaded and "
        f"events are sorted by (timestamp, stream_id, sequence_number)."
    )
