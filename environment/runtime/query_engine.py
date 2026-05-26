"""Query engine module.

Executes range and k-nearest-neighbor queries against the spatial index.
Computes per-window statistics for batch processing of queries.
"""

import csv
import os
import configparser


class QueryEngine:
    """Processes spatial queries in configurable batch windows."""

    def __init__(self, config_path, index):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._index = index
        self._data_dir = os.path.join(
            os.path.dirname(config_path),
            self._config.get("feeds", "data_dir")
        )
        self._batch_size = self._config.getint("queries", "batch_size")
        self._knn_k = self._config.getint("queries", "knn_k")

    def execute_range_queries(self):
        """Execute all range queries and return results with window stats."""
        queries_file = os.path.join(
            self._data_dir,
            self._config.get("queries", "range_queries_file")
        )
        queries = self._load_range_queries(queries_file)
        results = []
        window_stats = {}

        for i in range(0, len(queries), self._batch_size):
            batch = queries[i:i + self._batch_size]
            batch_results = []

            for q in batch:
                hits = self._index.range_query(
                    q["x_min"], q["y_min"], q["x_max"], q["y_max"]
                )
                batch_results.append({
                    "query_id": q["query_id"],
                    "hit_count": len(hits),
                    "hits": [
                        {"id": h["id"], "feed_id": h["feed_id"],
                         "x": h["x"], "y": h["y"], "label": h["label"]}
                        for h in hits
                    ],
                })

            results.extend(batch_results)

            # Compute window statistics
            window_id = f"window_{i // self._batch_size}"
            for br in batch_results:
                for hit in br["hits"]:
                    feed = hit["feed_id"]
                    if feed not in window_stats:
                        window_stats[feed] = 0
                    window_stats[feed] += br["hit_count"]

        return results, window_stats

    def execute_knn_queries(self):
        """Execute all KNN queries and return results."""
        queries_file = os.path.join(
            self._data_dir,
            self._config.get("queries", "knn_queries_file")
        )
        queries = self._load_knn_queries(queries_file)
        results = []

        for q in queries:
            neighbors = self._index.knn_query(q["x"], q["y"], self._knn_k)
            results.append({
                "query_id": q["query_id"],
                "center": {"x": q["x"], "y": q["y"]},
                "neighbors": neighbors,
            })

        return results

    def compute_batch_statistics(self, range_results):
        """Compute per-batch-window point counts.

        Processes range query results in batch windows and computes
        the point count per feed for each window. The final statistics
        should reflect the counts from the last window processed.
        """
        feed_counts = {}

        for i in range(0, len(range_results), self._batch_size):
            batch = range_results[i:i + self._batch_size]
            window_snapshot = {}

            for result in batch:
                for hit in result["hits"]:
                    feed = hit["feed_id"]
                    if feed not in window_snapshot:
                        window_snapshot[feed] = 0
                    window_snapshot[feed] += 1

            # Accumulate across windows
            for feed, count in window_snapshot.items():
                if feed not in feed_counts:
                    feed_counts[feed] = 0
                feed_counts[feed] += count

        return feed_counts

    def _load_range_queries(self, filepath):
        """Load range queries from CSV."""
        queries = []
        with open(filepath, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                queries.append({
                    "query_id": row["query_id"],
                    "x_min": float(row["x_min"]),
                    "y_min": float(row["y_min"]),
                    "x_max": float(row["x_max"]),
                    "y_max": float(row["y_max"]),
                })
        return queries

    def _load_knn_queries(self, filepath):
        """Load KNN queries from CSV."""
        queries = []
        with open(filepath, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                queries.append({
                    "query_id": row["query_id"],
                    "x": float(row["x"]),
                    "y": float(row["y"]),
                    "k": int(row["k"]),
                })
        return queries
