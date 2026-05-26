# Spatial Index Repair — Debugging Task

## Overview

A geospatial indexing engine ingests point location data from multiple feed sources, constructs an R-tree spatial index, and executes range and k-nearest-neighbor (KNN) queries against the indexed data. The system processes feeds in configurable batches and produces JSON output containing query results and index structure statistics.

## System Environment

- **Language**: Python 3.11
- **Runtime**: `/app/runtime/` (source, config, data, output)
- **Global system-wide tooling**: `uv` and `pytest` are available

## Processing Stages

1. **Feed Loading** — Reads CSV feed files (sensor, landmark, zone) based on the active feeds configuration. Each feed provides geospatial point records with coordinates, labels, timestamps, and per-feed insertion order.

2. **Index Construction** — Builds an R-tree spatial index from the loaded records. The tree uses rtree-specific parameters from the `[indexing.rtree]` configuration section for leaf node capacity and splitting behavior.

3. **Query Execution** — Runs range queries (bounding box containment) and KNN queries (nearest neighbors by Euclidean distance). KNN results are sorted deterministically by `(distance, feed_id, insert_order)` to handle ties.

4. **Batch Statistics** — Processes range query results in configurable batch windows and computes per-feed point counts. The final statistics represent the counts from the last processing window.

5. **Output Generation** — Writes query results and index statistics to JSON files in the output directory.

## Problem

The engine runs without errors but produces incorrect results:

- Some feed records appear to be missing from the index entirely
- The R-tree structure has unexpected properties (no node splitting despite many records)
- Batch statistics report inflated counts that exceed the actual number of records
- KNN query results show non-deterministic ordering for equidistant points

## Expected Correct Output

When all defects are fixed:

- All 55 records (20 sensor + 18 landmark + 17 zone) should be indexed
- The R-tree should use a leaf capacity of 8, producing a tree of depth 2 with 9 splits
- Batch window statistics should report per-feed counts from the final window only: sensor=20, landmark=18, zone=17
- KNN results should be deterministically ordered by (distance, feed_id, insert_order)

## Output Schema

### `/app/runtime/output/query_results.json`

| Field | Type | Description |
|-------|------|-------------|
| `range_queries` | list | List of range query result objects |
| `range_queries[].query_id` | string | Identifier of the range query |
| `range_queries[].hit_count` | integer | Number of points found in range |
| `range_queries[].hits` | list | List of hit record objects |
| `range_queries[].hits[].id` | string | Record identifier |
| `range_queries[].hits[].feed_id` | string | Source feed name |
| `range_queries[].hits[].x` | float | X coordinate |
| `range_queries[].hits[].y` | float | Y coordinate |
| `range_queries[].hits[].label` | string | Record label |
| `knn_queries` | list | List of KNN query result objects |
| `knn_queries[].query_id` | string | Identifier of the KNN query |
| `knn_queries[].center` | object | Query center point with x, y |
| `knn_queries[].neighbors` | list | Ordered list of nearest neighbors |
| `knn_queries[].neighbors[].id` | string | Neighbor record identifier |
| `knn_queries[].neighbors[].feed_id` | string | Neighbor source feed |
| `knn_queries[].neighbors[].x` | float | Neighbor X coordinate |
| `knn_queries[].neighbors[].y` | float | Neighbor Y coordinate |
| `knn_queries[].neighbors[].label` | string | Neighbor label |
| `knn_queries[].neighbors[].distance` | float | Euclidean distance from center |
| `total_records_indexed` | integer | Total number of records in the index |

### `/app/runtime/output/index_stats.json`

| Field | Type | Description |
|-------|------|-------------|
| `tree_depth` | integer | Depth of the R-tree structure |
| `max_leaf_capacity` | integer | Maximum entries per leaf node |
| `split_count` | integer | Number of node splits during construction |
| `total_indexed` | integer | Total number of indexed records |
| `batch_window_stats` | object | Per-feed point counts from final batch window |
| `batch_window_stats.sensor` | integer | Sensor feed count in final window |
| `batch_window_stats.landmark` | integer | Landmark feed count in final window |
| `batch_window_stats.zone` | integer | Zone feed count in final window |
| `window_feed_summary` | object | Per-feed summary from range query execution |

## Key Files

| File | Purpose |
|------|---------|
| `/app/runtime/config.ini` | Configuration with feed list, indexing parameters, and query settings |
| `/app/runtime/feed_loader.py` | Loads and filters spatial records from CSV feeds |
| `/app/runtime/rtree_index.py` | R-tree index implementation with insert, range query, and KNN |
| `/app/runtime/query_engine.py` | Executes queries in batch windows and computes statistics |
| `/app/runtime/run_spatial.py` | Main entry point orchestrating the full process |
| `/app/runtime/data/sensor_feed.csv` | Sensor location records (20 entries) |
| `/app/runtime/data/landmark_feed.csv` | Landmark location records (18 entries) |
| `/app/runtime/data/zone_feed.csv` | Zone location records (17 entries) |
| `/app/runtime/data/range_queries.csv` | Range query definitions (5 queries) |
| `/app/runtime/data/knn_queries.csv` | KNN query definitions (3 queries) |

## Your Task

Identify and fix defects in the runtime source files under `/app/runtime/`. The data files and query definitions are correct — the bugs are in the Python source code and its interaction with the configuration file. Focus on:

- How feed names are parsed from the configuration
- Which configuration section provides indexing parameters
- How batch window statistics are aggregated across windows
- How KNN results handle distance ties in sorting
