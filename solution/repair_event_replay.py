#!/usr/bin/env python3
"""Repair script for the event store replay engine.

Patches four defects in the runtime source code and re-runs the engine
to produce correct output.
"""

import os
import sys


def patch_stream_loader():
    """Fix Bug A: whitespace in comma-separated aggregate list parsing."""
    path = "/app/runtime/stream_loader.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'self._active_aggregates = set(raw_aggregates.split(","))',
        'self._active_aggregates = set(item.strip() for item in raw_aggregates.split(","))'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_event_projector():
    """Fix Bug B: read snapshot_interval from correct config section."""
    path = "/app/runtime/event_projector.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        '"projection", "snapshot_interval"',
        '"projection.materialized", "snapshot_interval"'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_replay_engine():
    """Fix Bug C: use epoch snapshot replacement instead of accumulation."""
    path = "/app/runtime/replay_engine.py"
    with open(path, "r") as f:
        content = f.read()
    old_block = """            # Track aggregate counts across epochs
            for agg, count in epoch_snapshot.items():
                if agg not in aggregate_totals:
                    aggregate_totals[agg] = 0
                aggregate_totals[agg] += count

        return replayed, aggregate_totals"""
    new_block = """            # Track only current epoch counts
            aggregate_totals = epoch_snapshot

        return replayed, aggregate_totals"""
    content = content.replace(old_block, new_block)
    with open(path, "w") as f:
        f.write(content)


def patch_event_ordering():
    """Fix Bug D: add aggregate_id to sort key for deterministic ordering."""
    path = "/app/runtime/event_ordering.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'key=lambda e: (e["timestamp"], e["seq_number"])',
        'key=lambda e: (e["timestamp"], e["aggregate_id"], e["seq_number"])'
    )
    with open(path, "w") as f:
        f.write(content)


def main():
    """Apply all patches and re-run the engine."""
    patch_stream_loader()
    patch_event_projector()
    patch_replay_engine()
    patch_event_ordering()

    # Re-run engine with fixed code
    sys.path.insert(0, "/app")
    for key in list(sys.modules.keys()):
        if key.startswith("runtime"):
            del sys.modules[key]
    from runtime.run_replay import main as run_main
    run_main()


if __name__ == "__main__":
    main()
