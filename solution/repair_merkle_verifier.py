#!/usr/bin/env python3
"""Repair script for the merkle proof verification engine.

Patches four defects in the runtime source code and re-runs the engine
to produce correct output.
"""

import os
import sys


def patch_chain_registry():
    """Fix Bug A: whitespace in comma-separated chain list."""
    path = "/app/runtime/chain_registry.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'return set(raw.split(","))',
        'return set(item.strip() for item in raw.split(","))'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_verifier_rounds():
    """Fix Bug B: off-by-one in verification round loop."""
    path = "/app/runtime/verifier_engine.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'for round_num in range(self._rounds - 1):',
        'for round_num in range(self._rounds):'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_depth_transition():
    """Fix Bug C: depth transition comparison and window accumulation."""
    path = "/app/runtime/verifier_engine.py"
    with open(path, "r") as f:
        content = f.read()
    # Fix comparison: > to >=
    content = content.replace(
        '                if proof["depth"] > prev_depth:',
        '                if proof["depth"] >= prev_depth:'
    )
    # Fix accumulation: += to = for window assignment
    content = content.replace(
        '                chain_metrics[chain]["proof_count"] += snap["proof_count"]\n                chain_metrics[chain]["depth_transitions"] += snap["depth_transitions"]\n                chain_metrics[chain]["total_depth"] += snap["total_depth"]',
        '                chain_metrics[chain]["proof_count"] = snap["proof_count"]\n                chain_metrics[chain]["depth_transitions"] = snap["depth_transitions"]\n                chain_metrics[chain]["total_depth"] = snap["total_depth"]'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_sort_key():
    """Fix Bug D: sort by position instead of leaf_hash."""
    path = "/app/runtime/verifier_engine.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'key=lambda p: (p["timestamp"], p["leaf_hash"], p["seq"])',
        'key=lambda p: (p["timestamp"], p["position"], p["seq"])'
    )
    with open(path, "w") as f:
        f.write(content)


if __name__ == "__main__":
    patch_chain_registry()
    patch_verifier_rounds()
    patch_depth_transition()
    patch_sort_key()

    # Re-run engine with fixed code
    sys.path.insert(0, "/app")
    for key in list(sys.modules.keys()):
        if key.startswith("runtime"):
            del sys.modules[key]
    from runtime.run_verifier import main as run_main
    run_main()
