"""Main entry point for the spatial indexing engine.

Orchestrates feed loading, index construction, query execution,
and output generation. Results are written as JSON to the output directory.
"""

import json
import os

from runtime.feed_loader import FeedLoader
from runtime.rtree_index import RTreeIndex
from runtime.query_engine import QueryEngine


def main():
    """Run the spatial index engine end-to-end."""
    config_path = os.path.join(os.path.dirname(__file__), "config.ini")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Stage 1: Load feed data
    loader = FeedLoader(config_path)
    records = loader.load_all_records()

    # Stage 2: Build spatial index
    index = RTreeIndex(config_path)
    for record in records:
        index.insert(record)

    # Stage 3: Execute queries
    engine = QueryEngine(config_path, index)
    range_results, window_stats = engine.execute_range_queries()
    knn_results = engine.execute_knn_queries()

    # Stage 4: Compute batch statistics
    batch_stats = engine.compute_batch_statistics(range_results)

    # Stage 5: Write outputs
    query_output = {
        "range_queries": range_results,
        "knn_queries": knn_results,
        "total_records_indexed": index.size,
    }

    index_stats = {
        "tree_depth": index.depth,
        "max_leaf_capacity": index.max_leaf_capacity,
        "split_count": index.split_count,
        "total_indexed": index.size,
        "batch_window_stats": batch_stats,
        "window_feed_summary": window_stats,
    }

    with open(os.path.join(output_dir, "query_results.json"), "w") as f:
        json.dump(query_output, f, indent=2)

    with open(os.path.join(output_dir, "index_stats.json"), "w") as f:
        json.dump(index_stats, f, indent=2)


if __name__ == "__main__":
    main()
