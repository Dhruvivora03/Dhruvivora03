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
# Fix Bug 1: diffusion_engine.py - missing own-component increment
# after EQUILIBRATE
# ============================================================

engine_path = "/app/runtime/diffusion_engine.py"
with open(engine_path, "r") as f:
    engine_code = f.read()

# Find the apply_equilibrate method and add the increment after the merge loop
# The bug is that after the for loop in apply_equilibrate, self._energy[self.node_id] += 1 is missing
# We locate the end of the for loop (last line: self._energy[node] = max(...)) and add the increment after

# Replace the method body: add increment after the max line
engine_code = re.sub(
    r'(    def apply_equilibrate\(self, neighbor_state\):.*?'
    r'self._energy\[node\] = max\(self._energy\[node\], incoming\))',
    r'''\1
        self._energy[self.node_id] += 1''',
    engine_code,
    flags=re.DOTALL
)

with open(engine_path, "w") as f:
    f.write(engine_code)


# ============================================================
# Fix Bug 2: lattice_analyzer.py - independence predicate checks
# equality instead of incomparability
# ============================================================

analyzer_path = "/app/runtime/lattice_analyzer.py"
with open(analyzer_path, "r") as f:
    analyzer_code = f.read()

# Replace the buggy independence function body
# Old: uses vector_leq both ways (checks equality)
# New: uses not vector_dominates both ways (checks incomparability)
analyzer_code = re.sub(
    r'(def nodes_are_thermally_independent\(vec_a, vec_b\):).*?'
    r'return a_bounded_by_b and b_bounded_by_a',
    r'''def nodes_are_thermally_independent(vec_a, vec_b):
    """Determine if two lattice nodes have independent thermal profiles.

    Two nodes are independent when neither vector dominates the other
    (incomparability in the partial order of component-wise comparison).
    """
    return not vector_dominates(vec_a, vec_b) and not vector_dominates(vec_b, vec_a)''',
    analyzer_code,
    flags=re.DOTALL
)


# ============================================================
# Fix Bug 3: lattice_analyzer.py - priority sorts by recency
# instead of by vector sum
# ============================================================

# Replace the buggy priority function
analyzer_code = re.sub(
    r'(def compute_simulation_priority\(nodes, vectors, events\):).*?'
    r'return sorted\(nodes, key=lambda n: last_seq\.get\(n, 0\)\)',
    r'''def compute_simulation_priority(nodes, vectors, events):
    """Determine simulation scheduling priority for lattice nodes.

    Priority is determined by total accumulated energy (vector sum).
    Nodes with lower energy sums are scheduled first to balance the lattice.
    """
    return sorted(nodes, key=lambda n: sum(vectors[n]))''',
    analyzer_code,
    flags=re.DOTALL
)

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
