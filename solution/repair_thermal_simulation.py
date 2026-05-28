"""
Repair script for the lattice thermal diffusion simulation.
Fixes bugs in diffusion_engine.py and lattice_analyzer.py, then re-runs
the simulation to produce correct output.
"""

import sys
import os
import re

sys.path.insert(0, "/app/runtime")

# ============================================================
# Fix Bug 1: diffusion_engine.py - EQUILIBRATE_MODE set to "observe"
# should be "participate" to enable self-increment
# ============================================================

engine_path = "/app/runtime/diffusion_engine.py"
with open(engine_path, "r") as f:
    engine_code = f.read()

# Change the mode from "observe" to "participate"
engine_code = re.sub(
    r'EQUILIBRATE_MODE\s*=\s*"observe"',
    'EQUILIBRATE_MODE = "participate"',
    engine_code
)

with open(engine_path, "w") as f:
    f.write(engine_code)


# ============================================================
# Fix Bug 2: lattice_analyzer.py - independence uses causal-cone
# disjointness instead of partial-order incomparability
# ============================================================

analyzer_path = "/app/runtime/lattice_analyzer.py"
with open(analyzer_path, "r") as f:
    analyzer_code = f.read()

# Replace the causal-cone based independence with non-dominance check
old_independence = re.compile(
    r'def nodes_are_thermally_independent\(vec_a, vec_b\):.*?'
    r'return _cones_are_disjoint\(cone_a, cone_b\)',
    re.DOTALL
)

new_independence = '''def nodes_are_thermally_independent(vec_a, vec_b):
    """Determine if two lattice nodes have independent thermal profiles.

    Two nodes are independent when neither vector dominates the other
    in the component-wise partial order (incomparability).
    """
    return not vector_dominates(vec_a, vec_b) and not vector_dominates(vec_b, vec_a)'''

analyzer_code = old_independence.sub(new_independence, analyzer_code)


# ============================================================
# Fix Bug 3: lattice_analyzer.py - priority uses L2 norm (Euclidean
# magnitude) instead of simple sum (total accumulated energy)
# ============================================================

old_priority = re.compile(
    r'def compute_simulation_priority\(nodes, vectors, events\):.*?'
    r'return sorted\(nodes, key=energy_magnitude\)',
    re.DOTALL
)

new_priority = '''def compute_simulation_priority(nodes, vectors, events):
    """Determine simulation scheduling priority for lattice nodes.

    Priority is determined by total accumulated energy (sum of all
    vector components). Nodes with lower total energy are scheduled first.
    """
    return sorted(nodes, key=lambda n: sum(vectors[n]))'''

analyzer_code = old_priority.sub(new_priority, analyzer_code)

with open(analyzer_path, "w") as f:
    f.write(analyzer_code)


# ============================================================
# Re-run the simulation with fixed code
# ============================================================

# Remove old output files
for f in ["/app/runtime/thermal_state.jsonl", "/app/runtime/thermal_summary.json"]:
    if os.path.exists(f):
        os.remove(f)

# Clear cached modules
for mod_name in list(sys.modules.keys()):
    if mod_name in ("diffusion_engine", "lattice_analyzer", "thermal_report",
                    "run_simulation", "log_parser"):
        del sys.modules[mod_name]

from run_simulation import run
run()
