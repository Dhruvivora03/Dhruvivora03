"""
Repair script for the token-flow-repair task.
Fixes 3 bugs in the dataflow analysis pipeline:

1. liveness_engine.py: Transfer function subtracts USE instead of DEF
   Fix: LiveIn(n) = USE(n) ∪ (LiveOut(n) - DEF(n))

2. interference_builder.py: Uses OR instead of AND for interference check
   Fix: Two variables interfere when BOTH are live at the same program point

3. allocation_scorer.py: Uses def count instead of interference degree
   Fix: Priority is determined by degree in the interference graph
"""

import os
import re


def get_runtime_dir():
    """Find the runtime directory."""
    # Check common locations - prefer project-local paths first
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "environment", "runtime"),
        "/app/runtime",
    ]
    for candidate in candidates:
        if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, "liveness_engine.py")):
            return candidate
    raise FileNotFoundError("Cannot find runtime directory")


def fix_liveness_engine(filepath):
    """
    Fix Bug 1: The transfer function incorrectly subtracts USE(n) from LiveOut(n)
    instead of subtracting DEF(n).

    Incorrect: LiveIn(n) = USE(n) ∪ (LiveOut(n) - USE(n))
    Correct:   LiveIn(n) = USE(n) ∪ (LiveOut(n) - DEF(n))
    """
    with open(filepath, 'r') as f:
        content = f.read()

    # Fix the transfer function: change "- use_set" to "- def_set" in the flow_through line
    content = content.replace(
        "flow_through = new_live_out - use_set",
        "flow_through = new_live_out - def_set"
    )

    with open(filepath, 'w') as f:
        f.write(content)


def fix_interference_builder(filepath):
    """
    Fix Bug 2: The interference check uses OR instead of AND.
    Two variables should interfere only when BOTH are live at the same point.

    Incorrect: if reg_a in live_at_point or reg_b in live_at_point
    Correct:   if reg_a in live_at_point and reg_b in live_at_point
    """
    with open(filepath, 'r') as f:
        content = f.read()

    # Fix the interference check: change "or" to "and"
    content = content.replace(
        "if reg_a in live_at_point or reg_b in live_at_point:",
        "if reg_a in live_at_point and reg_b in live_at_point:"
    )

    with open(filepath, 'w') as f:
        f.write(content)


def fix_allocation_scorer(filepath):
    """
    Fix Bug 3: Priority uses definition count instead of interference degree.
    The correct metric is the degree in the interference graph (most constrained first).

    Incorrect: score = def_counts.get(reg, 0)
    Correct:   score = len(interference[reg])
    """
    with open(filepath, 'r') as f:
        content = f.read()

    # Fix the priority computation: use interference degree instead of def count
    content = content.replace(
        "score = def_counts.get(reg, 0)",
        "score = len(interference[reg])"
    )

    with open(filepath, 'w') as f:
        f.write(content)


def main():
    """Apply all fixes and re-run the analysis."""
    runtime_dir = get_runtime_dir()

    print("Applying fixes to dataflow analysis pipeline...")

    # Fix Bug 1: Liveness transfer function
    liveness_path = os.path.join(runtime_dir, "liveness_engine.py")
    print(f"  [1/3] Fixing liveness_engine.py (transfer function: USE -> DEF)")
    fix_liveness_engine(liveness_path)

    # Fix Bug 2: Interference criterion
    interference_path = os.path.join(runtime_dir, "interference_builder.py")
    print(f"  [2/3] Fixing interference_builder.py (criterion: OR -> AND)")
    fix_interference_builder(interference_path)

    # Fix Bug 3: Allocation priority metric
    scorer_path = os.path.join(runtime_dir, "allocation_scorer.py")
    print(f"  [3/3] Fixing allocation_scorer.py (metric: def_count -> degree)")
    fix_allocation_scorer(scorer_path)

    # Re-run the analysis
    print("\nRe-running analysis with fixes applied...")
    import sys
    sys.path.insert(0, runtime_dir)

    # Clear cached modules to pick up fixes
    modules_to_clear = [
        'bytecode_parser', 'liveness_engine', 
        'interference_builder', 'allocation_scorer', 
        'analysis_output', 'run_analysis'
    ]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]

    from run_analysis import main as run_main
    run_main()

    print("\nAll fixes applied and analysis re-run successfully!")


if __name__ == "__main__":
    main()
