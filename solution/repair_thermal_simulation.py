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
# Fix Bug 1: diffusion_engine.py - conditional increment only when
# peer reports higher self-value. Should always increment.
# ============================================================

engine_path = "/app/runtime/diffusion_engine.py"
with open(engine_path, "r") as f:
    lines = f.readlines()

# Find and fix the apply_equilibrate method
new_lines = []
skip_until_dedent = False
in_equilibrate = False
inserted_fix = False

i = 0
while i < len(lines):
    line = lines[i]

    # Detect start of apply_equilibrate
    if 'def apply_equilibrate(self, neighbor_state):' in line:
        in_equilibrate = True
        new_lines.append(line)
        i += 1
        continue

    if in_equilibrate:
        # Skip the own_before line
        if 'own_before = self._energy[self.node_id]' in line:
            i += 1
            continue

        # Replace the conditional block with unconditional increment
        if '# Attribute energy only for active knowledge acquisition' in line:
            # Skip the comment, if statement, and its body
            i += 1  # skip comment
            while i < len(lines) and ('if self._energy[self.node_id] > own_before' in lines[i]
                                       or 'self._energy[self.node_id] += 1' in lines[i]
                                       or 'self._active_equilibrations += 1' in lines[i]
                                       or lines[i].strip() == ''):
                i += 1
            # Insert unconditional increment
            new_lines.append('        self._energy[self.node_id] += 1\n')
            new_lines.append('\n')
            in_equilibrate = False
            inserted_fix = True
            continue

        # Detect end of method (next def or class)
        if line.strip().startswith('def ') and in_equilibrate and 'apply_equilibrate' not in line:
            in_equilibrate = False

    new_lines.append(line)
    i += 1

with open(engine_path, "w") as f:
    f.writelines(new_lines)


# ============================================================
# Fix Bug 2: lattice_analyzer.py - independence checks sign-consistency
# (monotone diff = comparable) instead of sign-inconsistency
# (mixed signs = incomparable = truly independent)
# ============================================================

analyzer_path = "/app/runtime/lattice_analyzer.py"
with open(analyzer_path, "r") as f:
    analyzer_code = f.read()

# Replace the independence function
old_independence = re.compile(
    r'def nodes_are_thermally_independent\(vec_a, vec_b\):.*?'
    r'return _is_sign_consistent\(diff\)',
    re.DOTALL
)

new_independence = '''def nodes_are_thermally_independent(vec_a, vec_b):
    """Determine if two lattice nodes have independent thermal profiles.

    Two nodes are independent when their difference vector has mixed signs
    (incomparable in the partial order -- neither uniformly dominates).
    """
    diff = _compute_difference(vec_a, vec_b)
    has_positive = any(d > 0 for d in diff)
    has_negative = any(d < 0 for d in diff)
    return has_positive and has_negative'''

analyzer_code = old_independence.sub(new_independence, analyzer_code)


# ============================================================
# Fix Bug 3: priority uses L2 norm instead of simple sum
# ============================================================

old_priority = re.compile(
    r'def compute_simulation_priority\(nodes, vectors, events\):.*?'
    r'return sorted\(nodes, key=energy_magnitude\)',
    re.DOTALL
)

new_priority = '''def compute_simulation_priority(nodes, vectors, events):
    """Determine simulation scheduling priority for lattice nodes.

    Priority is determined by total accumulated energy (sum of components).
    """
    return sorted(nodes, key=lambda n: sum(vectors[n]))'''

analyzer_code = old_priority.sub(new_priority, analyzer_code)

with open(analyzer_path, "w") as f:
    f.write(analyzer_code)


# ============================================================
# Re-run the simulation with fixed code
# ============================================================

for f in ["/app/runtime/thermal_state.jsonl", "/app/runtime/thermal_summary.json"]:
    if os.path.exists(f):
        os.remove(f)

for mod_name in list(sys.modules.keys()):
    if mod_name in ("diffusion_engine", "lattice_analyzer", "thermal_report",
                    "run_simulation", "log_parser"):
        del sys.modules[mod_name]

from run_simulation import run
run()
