#!/usr/bin/env python3
"""Repair script for the deadline task scheduling engine.

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


def patch_priority_queue_section():
    """Fix Bug B: read urgency multiplier from correct config section."""
    path = "/app/runtime/priority_queue.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        '"scheduling", "urgency_multiplier"',
        '"scheduling.deadline", "urgency_multiplier"'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_dependency_resolver_accumulation():
    """Fix Bug C: use assignment instead of accumulation for wave stats."""
    path = "/app/runtime/dependency_resolver.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        '                stream_counts[stream] += count',
        '                stream_counts[stream] = count'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_priority_queue_sort():
    """Fix Bug D: add stream_id to sort key for deterministic ordering."""
    path = "/app/runtime/priority_queue.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'key=lambda e: (-e["priority_score"], e["seq_number"])',
        'key=lambda e: (-e["priority_score"], e["stream_id"], e["seq_number"])'
    )
    with open(path, "w") as f:
        f.write(content)


def main():
    """Apply all patches and re-run the engine."""
    patch_stream_loader()
    patch_priority_queue_section()
    patch_dependency_resolver_accumulation()
    patch_priority_queue_sort()

    # Re-run engine with fixed code
    sys.path.insert(0, "/app")
    for key in list(sys.modules.keys()):
        if key.startswith("runtime"):
            del sys.modules[key]
    from runtime.run_scheduler import main as run_main
    run_main()


if __name__ == "__main__":
    main()
