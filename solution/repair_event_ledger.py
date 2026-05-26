#!/usr/bin/env python3
"""Repair script for the event sourcing ledger replay engine.

Patches four defects in the runtime source code and re-runs the engine
to produce correct output.
"""

import os
import sys


def patch_event_loader():
    """Fix Bug A: whitespace in comma-separated stream list parsing."""
    path = "/app/runtime/event_loader.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'self._active_streams = set(raw_streams.split(","))',
        'self._active_streams = set(item.strip() for item in raw_streams.split(","))'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_ledger_engine_section():
    """Fix Bug B: read window_size from correct config section."""
    path = "/app/runtime/ledger_engine.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'self._window_size = self._config.getint("replay", "window_size")',
        'self._window_size = self._config.getint("replay.streaming", "window_size")'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_ledger_engine_accumulation():
    """Fix Bug C: use assignment instead of accumulation for window projections."""
    path = "/app/runtime/ledger_engine.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        '                account_projections[acct] += balance',
        '                account_projections[acct] = balance'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_ledger_engine_sort():
    """Fix Bug D: add stream_id to sort key for deterministic ordering."""
    path = "/app/runtime/ledger_engine.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'return sorted(events, key=lambda e: (e["timestamp"], e["seq"]))',
        'return sorted(events, key=lambda e: (e["timestamp"], e["stream_id"], e["seq"]))'
    )
    with open(path, "w") as f:
        f.write(content)


def main():
    """Apply all patches and re-run the engine."""
    patch_event_loader()
    patch_ledger_engine_section()
    patch_ledger_engine_accumulation()
    patch_ledger_engine_sort()

    # Re-run engine with fixed code
    sys.path.insert(0, "/app")
    for key in list(sys.modules.keys()):
        if key.startswith("runtime"):
            del sys.modules[key]
    from runtime.run_ledger import main as run_main
    run_main()


if __name__ == "__main__":
    main()
