"""R-tree spatial index implementation.

Provides insertion, range queries, and k-nearest-neighbor lookups
over 2D point data. Uses a simplified R-tree structure with
configurable leaf capacity for node splitting.
"""

import math
import configparser


class RTreeIndex:
    """Simplified R-tree index for 2D point data.

    Maintains entries in leaf buckets with configurable capacity.
    When a bucket exceeds capacity, it splits into two. All buckets
    are tracked at the top level for query processing.
    """

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._max_leaf = self._config.getint("indexing", "max_leaf_capacity")
        self._buckets = [[]]
        self._size = 0
        self._splits = 0

    @property
    def size(self):
        return self._size

    @property
    def depth(self):
        """Tree depth based on number of buckets."""
        if len(self._buckets) <= 1:
            return 1
        return 2

    @property
    def max_leaf_capacity(self):
        return self._max_leaf

    @property
    def split_count(self):
        return self._splits

    def insert(self, record):
        """Insert a point record into the index."""
        best_bucket = self._choose_bucket(record)
        best_bucket.append(record)
        self._size += 1

        if len(best_bucket) > self._max_leaf:
            self._split_bucket(best_bucket)

    def _choose_bucket(self, record):
        """Choose the best bucket for insertion based on proximity."""
        if not self._buckets[0]:
            return self._buckets[0]

        best = None
        best_dist = float("inf")
        for bucket in self._buckets:
            if not bucket:
                return bucket
            cx = sum(e["x"] for e in bucket) / len(bucket)
            cy = sum(e["y"] for e in bucket) / len(bucket)
            dist = (record["x"] - cx) ** 2 + (record["y"] - cy) ** 2
            if dist < best_dist:
                best_dist = dist
                best = bucket
        return best

    def _split_bucket(self, bucket):
        """Split an overflowing bucket into two."""
        entries = sorted(bucket, key=lambda e: e["x"])
        mid = len(entries) // 2

        bucket.clear()
        bucket.extend(entries[:mid])

        new_bucket = entries[mid:]
        self._buckets.append(new_bucket)
        self._splits += 1

    def range_query(self, x_min, y_min, x_max, y_max):
        """Find all points within the given bounding box."""
        results = []
        for bucket in self._buckets:
            for entry in bucket:
                if (x_min <= entry["x"] <= x_max and
                        y_min <= entry["y"] <= y_max):
                    results.append(entry)
        return results

    def knn_query(self, x, y, k):
        """Find the k nearest neighbors to point (x, y).

        Returns results sorted by distance. For tied distances,
        results are ordered by insert_order.
        """
        # Note: insert_order is local to each feed
        all_entries = []
        for bucket in self._buckets:
            all_entries.extend(bucket)

        for entry in all_entries:
            dist = math.sqrt((entry["x"] - x) ** 2 + (entry["y"] - y) ** 2)
            entry["_distance"] = dist

        sorted_entries = sorted(
            all_entries,
            key=lambda e: (e["_distance"], e["insert_order"])
        )

        results = []
        for entry in sorted_entries[:k]:
            results.append({
                "id": entry["id"],
                "feed_id": entry["feed_id"],
                "x": entry["x"],
                "y": entry["y"],
                "label": entry["label"],
                "distance": round(entry["_distance"], 6),
            })
        return results

    def get_statistics(self):
        """Return index statistics."""
        return {
            "total_indexed": self._size,
            "tree_depth": self.depth,
            "max_leaf_capacity": self._max_leaf,
            "split_count": self._splits,
        }
