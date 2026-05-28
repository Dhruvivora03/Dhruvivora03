"""
Repair script for the warzone campaign state synchronization simulation.
Fixes bugs in influence_tracker.py and conflict_resolver.py, then re-runs
the simulation to produce correct output.
"""

import sys
import os
import re

sys.path.insert(0, "/app/runtime")

# ============================================================
# Fix Bug 1: influence_tracker.py - conditional increment only when
# ally reports higher self-value. Should always increment.
# ============================================================

engine_path = "/app/runtime/influence_tracker.py"
with open(engine_path, "r") as f:
    lines = f.readlines()

new_lines = []
in_rally = False
i = 0
while i < len(lines):
    line = lines[i]

    if 'def apply_rally(self, allied_state):' in line:
        in_rally = True
        new_lines.append(line)
        i += 1
        continue

    if in_rally:
        # Skip the own_before line
        if 'own_before = self._influence[self.zone_id]' in line:
            i += 1
            continue

        # Replace the conditional block with unconditional increment
        if '# Attribute influence only for active intelligence acquisition' in line:
            i += 1  # skip comment
            while i < len(lines) and ('if self._influence[self.zone_id] > own_before' in lines[i]
                                       or 'self._influence[self.zone_id] += 1' in lines[i]
                                       or 'self._active_rallies += 1' in lines[i]
                                       or lines[i].strip() == ''):
                i += 1
            new_lines.append('        self._influence[self.zone_id] += 1\n')
            new_lines.append('\n')
            in_rally = False
            continue

        if line.strip().startswith('def ') and 'apply_rally' not in line:
            in_rally = False

    new_lines.append(line)
    i += 1

with open(engine_path, "w") as f:
    f.writelines(new_lines)


# ============================================================
# Fix Bug 2: conflict_resolver.py - independence checks sign-consistency
# (monotone diff = comparable) instead of sign-inconsistency
# (mixed signs = incomparable = truly independent)
# ============================================================

analyzer_path = "/app/runtime/conflict_resolver.py"
with open(analyzer_path, "r") as f:
    analyzer_code = f.read()

old_independence = re.compile(
    r'def zones_are_operationally_independent\(vec_a, vec_b\):.*?'
    r'return _is_sign_consistent\(diff\)',
    re.DOTALL
)

new_independence = '''def zones_are_operationally_independent(vec_a, vec_b):
    """Determine if two zones have independent operational profiles.

    Two zones are independent when their difference vector has mixed signs
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
    r'def compute_deployment_priority\(zones, vectors, events\):.*?'
    r'return sorted\(zones, key=influence_magnitude\)',
    re.DOTALL
)

new_priority = '''def compute_deployment_priority(zones, vectors, events):
    """Determine deployment scheduling priority for contested zones.

    Priority is determined by total accumulated influence (sum of components).
    """
    return sorted(zones, key=lambda z: sum(vectors[z]))'''

analyzer_code = old_priority.sub(new_priority, analyzer_code)

with open(analyzer_path, "w") as f:
    f.write(analyzer_code)


# ============================================================
# Re-run the simulation with fixed code
# ============================================================

for f in ["/app/runtime/campaign_state.jsonl", "/app/runtime/campaign_summary.json"]:
    if os.path.exists(f):
        os.remove(f)

for mod_name in list(sys.modules.keys()):
    if mod_name in ("influence_tracker", "conflict_resolver", "war_report",
                    "run_campaign", "log_reader"):
        del sys.modules[mod_name]

from run_campaign import run
run()
