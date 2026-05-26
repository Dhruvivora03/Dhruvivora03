#!/usr/bin/env python3
"""Repair script for the task scheduler engine.

Patches four defects in the runtime source code and re-runs the engine
to produce correct output.
"""

import os
import sys


def patch_job_loader():
    """Fix Bug A: whitespace in comma-separated category list parsing."""
    path = "/app/runtime/job_loader.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'self._active_categories = set(raw_categories.split(","))',
        'self._active_categories = set(item.strip() for item in raw_categories.split(","))'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_scheduler_engine_section():
    """Fix Bug B: read epoch_size from correct config section."""
    path = "/app/runtime/scheduler_engine.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'self._epoch_size = self._config.getint("scheduling", "epoch_size")',
        'self._epoch_size = self._config.getint("scheduling.parallel", "epoch_size")'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_scheduler_engine_accumulation():
    """Fix Bug C: use assignment instead of accumulation for epoch resources."""
    path = "/app/runtime/scheduler_engine.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        '                epoch_resources[cat] += duration',
        '                epoch_resources[cat] = duration'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_scheduler_engine_sort():
    """Fix Bug D: add category_id to sort key for deterministic ordering."""
    path = "/app/runtime/scheduler_engine.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'ready.sort(key=lambda j: (-j["priority"], j["seq"]))',
        'ready.sort(key=lambda j: (-j["priority"], j["category_id"], j["seq"]))'
    )
    with open(path, "w") as f:
        f.write(content)


def main():
    """Apply all patches and re-run the engine."""
    patch_job_loader()
    patch_scheduler_engine_section()
    patch_scheduler_engine_accumulation()
    patch_scheduler_engine_sort()

    # Re-run engine with fixed code
    sys.path.insert(0, "/app")
    for key in list(sys.modules.keys()):
        if key.startswith("runtime"):
            del sys.modules[key]
    from runtime.run_scheduler import main as run_main
    run_main()


if __name__ == "__main__":
    main()
