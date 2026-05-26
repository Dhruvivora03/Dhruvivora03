#!/usr/bin/env python3
"""Repair script for the IR optimization engine.

Patches four defects in the runtime source code and re-runs the engine
to produce correct output.
"""

import os
import sys


def patch_module_loader():
    """Fix Bug A: whitespace in comma-separated module list parsing."""
    path = "/app/runtime/module_loader.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'return set(raw.split(","))',
        'return set(item.strip() for item in raw.split(","))'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_pass_engine_section():
    """Fix Bug B: read pass parameters from correct config section."""
    path = "/app/runtime/pass_engine.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'self._pass_depth = self._config.getint("optimizer", "pass_depth")',
        'self._pass_depth = self._config.getint("optimizer.passes", "pass_depth")'
    )
    content = content.replace(
        'self._inline_threshold = self._config.getint(\n            "optimizer", "inline_threshold"\n        )',
        'self._inline_threshold = self._config.getint(\n            "optimizer.passes", "inline_threshold"\n        )'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_pass_engine_accumulation():
    """Fix Bug C: use assignment instead of accumulation for window metrics."""
    path = "/app/runtime/pass_engine.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        '                module_metrics[mod]["total"] += counts["total"]\n                module_metrics[mod]["optimized"] += counts["optimized"]',
        '                module_metrics[mod]["total"] = counts["total"]\n                module_metrics[mod]["optimized"] = counts["optimized"]'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_pass_engine_sort():
    """Fix Bug D: add module_id to sort key for deterministic ordering."""
    path = "/app/runtime/pass_engine.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'key=lambda i: (i["timestamp"], i["seq"])',
        'key=lambda i: (i["timestamp"], i["module_id"], i["seq"])'
    )
    with open(path, "w") as f:
        f.write(content)


if __name__ == "__main__":
    patch_module_loader()
    patch_pass_engine_section()
    patch_pass_engine_accumulation()
    patch_pass_engine_sort()

    # Re-run engine with fixed code
    sys.path.insert(0, "/app")
    for key in list(sys.modules.keys()):
        if key.startswith("runtime"):
            del sys.modules[key]
    from runtime.run_optimizer import main as run_main
    run_main()
