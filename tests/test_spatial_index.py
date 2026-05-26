"""Test suite for the spatial indexing engine.

Validates query results and index statistics output by the engine.
Tests are structured in graduated difficulty from basic structural
checks to full correctness verification.
"""

import json
import os

OUTPUT_DIR = "/app/runtime/output"
QUERY_RESULTS_PATH = os.path.join(OUTPUT_DIR, "query_results.json")
INDEX_STATS_PATH = os.path.join(OUTPUT_DIR, "index_stats.json")


def _load_query_results():
    """Load query results JSON output."""
    with open(QUERY_RESULTS_PATH, "r") as f:
        return json.load(f)


def _load_index_stats():
    """Load index statistics JSON output."""
    with open(INDEX_STATS_PATH, "r") as f:
        return json.load(f)


# ============================================================
# EASY TESTS (pass even with buggy code)
# ============================================================


def test_output_files_exist():
    """Verify that the engine produces both expected output files."""
    assert os.path.exists(QUERY_RESULTS_PATH), (
        f"Missing output file: {QUERY_RESULTS_PATH}"
    )
    assert os.path.exists(INDEX_STATS_PATH), (
        f"Missing output file: {INDEX_STATS_PATH}"
    )


def test_query_results_structure():
    """Verify the top-level structure of query_results.json contains required keys."""
    data = _load_query_results()
    assert "range_queries" in data, "query_results.json missing 'range_queries' key"
    assert "knn_queries" in data, "query_results.json missing 'knn_queries' key"
    assert "total_records_indexed" in data, (
        "query_results.json missing 'total_records_indexed' key"
    )


def test_index_stats_structure():
    """Verify the top-level structure of index_stats.json contains required keys."""
    stats = _load_index_stats()
    required_keys = [
        "tree_depth", "max_leaf_capacity", "split_count",
        "total_indexed", "batch_window_stats", "window_feed_summary",
    ]
    for key in required_keys:
        assert key in stats, f"index_stats.json missing '{key}' key"


def test_range_queries_are_list():
    """Verify that range query results are returned as a list of results."""
    data = _load_query_results()
    assert isinstance(data["range_queries"], list), (
        "range_queries should be a list"
    )
    assert len(data["range_queries"]) == 5, (
        f"Expected 5 range query results, got {len(data['range_queries'])}"
    )


# ============================================================
# MEDIUM TESTS (require 1-2 bug fixes)
# ============================================================


def test_zone_feed_records_indexed():
    """Verify that zone feed records are included in the spatial index.

    The engine should index records from all configured active feeds
    including the zone feed. Check that zone records appear in range
    query results covering the zone feed coordinates.
    """
    data = _load_query_results()
    # RQ01 covers (11.50,45.00)-(13.50,46.00) which includes zone records
    rq01 = data["range_queries"][0]
    zone_hits = [h for h in rq01["hits"] if h["feed_id"] == "zone"]
    assert len(zone_hits) >= 5, (
        f"Expected at least 5 zone records in RQ01 range, got {len(zone_hits)}. "
        f"Check feed filtering in /app/runtime/feed_loader.py — "
        f"verify active_feeds parsing handles whitespace correctly."
    )


def test_correct_leaf_capacity():
    """Verify that the R-tree uses the correct maximum leaf node capacity.

    The spatial index should use the rtree-specific configuration for
    its leaf capacity parameter, resulting in proper tree structure.
    """
    stats = _load_index_stats()
    assert stats["max_leaf_capacity"] == 8, (
        f"Expected max_leaf_capacity=8, got {stats['max_leaf_capacity']}. "
        f"Check which config section is used in /app/runtime/rtree_index.py — "
        f"the rtree-specific parameters are in [indexing.rtree]."
    )


def test_batch_window_statistics():
    """Verify that batch window statistics reflect per-window counts correctly.

    The batch statistics should report the point counts from the final
    processing window, not accumulated totals across all windows.
    """
    stats = _load_index_stats()
    batch_stats = stats["batch_window_stats"]
    # With all feeds active and batch_size=2, the last window processes
    # only RQ05 (full range) giving: sensor=20, landmark=18, zone=17
    assert "zone" in batch_stats, (
        f"batch_window_stats missing 'zone' feed — "
        f"zone records must be indexed first (check feed loading)."
    )
    assert batch_stats["sensor"] == 20, (
        f"Expected batch_window_stats['sensor']=20, got {batch_stats['sensor']}. "
        f"Statistics should reflect the final window's counts, not accumulated totals. "
        f"Check /app/runtime/query_engine.py compute_batch_statistics method."
    )
    assert batch_stats["landmark"] == 18, (
        f"Expected batch_window_stats['landmark']=18, got {batch_stats['landmark']}."
    )
    assert batch_stats["zone"] == 17, (
        f"Expected batch_window_stats['zone']=17, got {batch_stats['zone']}."
    )


# ============================================================
# HARD TESTS (require 3-4 bug fixes together)
# ============================================================


def test_knn_neighbor_ordering():
    """Verify correct ordering of k-nearest-neighbor results.

    KNN results must be sorted by (distance, feed_id, insert_order) to
    produce deterministic ordering when multiple points share the same
    distance from the query center. Check the sort key in
    /app/runtime/rtree_index.py knn_query method.
    """
    data = _load_query_results()
    knn01 = data["knn_queries"][0]
    neighbors = knn01["neighbors"]

    # First neighbor: Z005 at distance 0 (exact center hit)
    assert neighbors[0]["id"] == "Z005", (
        f"KNN01 first neighbor should be Z005 (distance=0), got {neighbors[0]['id']}. "
        f"Zone feed records must be indexed — check /app/runtime/feed_loader.py."
    )
    assert neighbors[0]["distance"] == 0.0, (
        f"KNN01 first neighbor distance should be 0.0, got {neighbors[0]['distance']}."
    )

    # Second neighbor: S017 at distance ~0.1
    assert neighbors[1]["id"] == "S017", (
        f"KNN01 second neighbor should be S017, got {neighbors[1]['id']}."
    )

    # Third and fourth: L001 and Z017 both at distance ~0.141421
    # Correct sort by feed_id: landmark < zone
    assert neighbors[2]["id"] == "L001", (
        f"KNN01 third neighbor should be L001 (landmark before zone at same distance), "
        f"got {neighbors[2]['id']}. Check sort key includes feed_id in "
        f"/app/runtime/rtree_index.py — sort should be (distance, feed_id, insert_order)."
    )
    assert neighbors[3]["id"] == "Z017", (
        f"KNN01 fourth neighbor should be Z017, got {neighbors[3]['id']}."
    )


def test_total_records_indexed():
    """Verify the correct total number of records are indexed.

    All three feeds (sensor: 20, landmark: 18, zone: 17) should be loaded
    and indexed, giving a total of 55 records.
    """
    data = _load_query_results()
    assert data["total_records_indexed"] == 55, (
        f"Expected 55 total records indexed (20+18+17), "
        f"got {data['total_records_indexed']}. "
        f"Check that all active feeds are loaded correctly."
    )
    stats = _load_index_stats()
    assert stats["total_indexed"] == 55, (
        f"Expected total_indexed=55, got {stats['total_indexed']}."
    )


def test_full_range_query_accuracy():
    """Verify full-range query returns all indexed records with correct counts.

    RQ05 covers the entire data space and should return all 55 records
    from all three feeds with correct per-feed counts.
    """
    data = _load_query_results()
    rq05 = data["range_queries"][4]
    assert rq05["hit_count"] == 55, (
        f"Full-range query RQ05 should return 55 hits, got {rq05['hit_count']}."
    )
    feed_counts = {}
    for hit in rq05["hits"]:
        feed = hit["feed_id"]
        feed_counts[feed] = feed_counts.get(feed, 0) + 1
    assert feed_counts.get("sensor", 0) == 20, (
        f"Expected 20 sensor records in full range, got {feed_counts.get('sensor', 0)}."
    )
    assert feed_counts.get("landmark", 0) == 18, (
        f"Expected 18 landmark records in full range, got {feed_counts.get('landmark', 0)}."
    )
    assert feed_counts.get("zone", 0) == 17, (
        f"Expected 17 zone records in full range, got {feed_counts.get('zone', 0)}."
    )
