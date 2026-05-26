#!/usr/bin/env python3
"""Repair script for the spatial indexing engine.

Patches four defects in the runtime source code and re-runs the engine
to produce correct output.
"""

import os
import sys


def patch_feed_loader():
    """Fix Bug A: whitespace in comma-separated feed list parsing."""
    path = "/app/runtime/feed_loader.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'self._active_feeds = set(raw_feeds.split(","))',
        'self._active_feeds = set(item.strip() for item in raw_feeds.split(","))'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_rtree_index_section():
    """Fix Bug B: read leaf capacity from correct config section."""
    path = "/app/runtime/rtree_index.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'self._max_leaf = self._config.getint("indexing", "max_leaf_capacity")',
        'self._max_leaf = self._config.getint("indexing.rtree", "max_leaf_capacity")'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_query_engine_accumulation():
    """Fix Bug C: use assignment instead of accumulation for batch stats."""
    path = "/app/runtime/query_engine.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        '                feed_counts[feed] += count',
        '                feed_counts[feed] = count'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_rtree_knn_sort():
    """Fix Bug D: add feed_id to KNN sort key for deterministic ordering."""
    path = "/app/runtime/rtree_index.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'key=lambda e: (e["_distance"], e["insert_order"])',
        'key=lambda e: (e["_distance"], e["feed_id"], e["insert_order"])'
    )
    with open(path, "w") as f:
        f.write(content)


def main():
    """Apply all patches and re-run the engine."""
    patch_feed_loader()
    patch_rtree_index_section()
    patch_query_engine_accumulation()
    patch_rtree_knn_sort()

    # Re-run engine with fixed code
    sys.path.insert(0, "/app")
    for key in list(sys.modules.keys()):
        if key.startswith("runtime"):
            del sys.modules[key]
    from runtime.run_spatial import main as run_main
    run_main()


if __name__ == "__main__":
    main()
