#!/usr/bin/env python3
"""Repair script for the event store replay engine.

Patches four defects in the runtime source code and re-runs the engine
to produce correct output.
"""

import os
import sys


def patch_stream_loader():
    """Fix Bug A: whitespace in comma-separated stream list parsing."""
    path = "/app/runtime/stream_loader.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'self._active_streams = set(raw_streams.split(","))',
        'self._active_streams = set(item.strip() for item in raw_streams.split(","))'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_event_store_section():
    """Fix Bug B: read snapshot_interval from correct config section."""
    path = "/app/runtime/event_store.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'self._snapshot_interval = self._config.getint(\n            "projection", "snapshot_interval"\n        )',
        'self._snapshot_interval = self._config.getint(\n            "projection.incremental", "snapshot_interval"\n        )'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_projection_accumulation():
    """Fix Bug C: use assignment instead of accumulation for window aggregates."""
    path = "/app/runtime/projection_engine.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        '                stream_totals[stream] += count',
        '                stream_totals[stream] = count'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_event_store_sort():
    """Fix Bug D: add stream_id to replay sort key for deterministic ordering."""
    path = "/app/runtime/event_store.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'key=lambda e: (e["timestamp"], e["sequence_number"])',
        'key=lambda e: (e["timestamp"], e["stream_id"], e["sequence_number"])'
    )
    with open(path, "w") as f:
        f.write(content)


def main():
    """Apply all patches and re-run the engine."""
    patch_stream_loader()
    patch_event_store_section()
    patch_projection_accumulation()
    patch_event_store_sort()

    # Re-run engine with fixed code
    sys.path.insert(0, "/app")
    for key in list(sys.modules.keys()):
        if key.startswith("runtime"):
            del sys.modules[key]
    from runtime.run_replay import main as run_main
    run_main()


if __name__ == "__main__":
    main()
