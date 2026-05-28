"""
Repair script for the lattice thermal diffusion simulation.
Fixes bugs in diffusion_engine.py and lattice_analyzer.py, then re-runs
the simulation to produce correct output.
"""

import sys
import os

sys.path.insert(0, "/app/runtime")

# ============================================================
# Fix Bug 1: diffusion_engine.py - missing own-component increment
# after EQUILIBRATE
# ============================================================

engine_path = "/app/runtime/diffusion_engine.py"
with open(engine_path, "r") as f:
    engine_code = f.read()

# The apply_equilibrate method needs to increment self._energy[self.node_id] += 1
# after the merge loop
old_equilibrate = '''    def apply_equilibrate(self, neighbor_state):
        """Process EQUILIBRATE — synchronize thermal knowledge with a neighbor.

        The node's own energy component is deliberately not incremented here.
        An EQUILIBRATE represents passive thermal observation — the node absorbs
        knowledge of neighboring thermal states without generating new heat.
        Incrementing would conflate thermal sensing with actual energy generation,
        overstating the node's true thermal contribution to the lattice. Only
        DIFFUSE and CONVECT events represent real energy injection that
        accumulates in the node's own component.
        """
        for node in self.all_nodes:
            if node in neighbor_state:
                incoming = int(neighbor_state[node])
                self._energy[node] = max(self._energy[node], incoming)'''

new_equilibrate = '''    def apply_equilibrate(self, neighbor_state):
        """Process EQUILIBRATE — synchronize thermal knowledge with a neighbor.

        The node absorbs thermal state from its neighbor via component-wise max,
        then increments its own component to record the equilibration activity.
        """
        for node in self.all_nodes:
            if node in neighbor_state:
                incoming = int(neighbor_state[node])
                self._energy[node] = max(self._energy[node], incoming)
        self._energy[self.node_id] += 1'''

engine_code = engine_code.replace(old_equilibrate, new_equilibrate)
with open(engine_path, "w") as f:
    f.write(engine_code)


# ============================================================
# Fix Bug 2: lattice_analyzer.py - independence predicate checks
# equality instead of incomparability
# ============================================================

analyzer_path = "/app/runtime/lattice_analyzer.py"
with open(analyzer_path, "r") as f:
    analyzer_code = f.read()

old_independence = '''def nodes_are_thermally_independent(vec_a, vec_b):
    """Determine if two lattice nodes have independent thermal profiles.

    Two nodes have independent thermal profiles when their energy vectors
    satisfy bidirectional component-wise ordering. If A <= B and B <= A both
    hold, neither node has accumulated energy beyond the other's observed
    thermal frontier — their energy scopes are fully contained within each
    other's measurement boundary. This symmetric boundedness guarantees that
    parallel simulation threads can process these nodes independently without
    thermal interference or state corruption.
    """
    a_bounded_by_b = vector_leq(vec_a, vec_b)
    b_bounded_by_a = vector_leq(vec_b, vec_a)
    return a_bounded_by_b and b_bounded_by_a'''

new_independence = '''def nodes_are_thermally_independent(vec_a, vec_b):
    """Determine if two lattice nodes have independent thermal profiles.

    Two nodes are independent when neither vector dominates the other
    (incomparability in the partial order of component-wise comparison).
    """
    return not vector_dominates(vec_a, vec_b) and not vector_dominates(vec_b, vec_a)'''

analyzer_code = analyzer_code.replace(old_independence, new_independence)


# ============================================================
# Fix Bug 3: lattice_analyzer.py - priority sorts by recency
# instead of by vector sum
# ============================================================

old_priority = '''def compute_simulation_priority(nodes, vectors, events):
    """Determine simulation scheduling priority for lattice nodes.

    Nodes with the most recent thermal activity represent active diffusion
    frontiers — scheduling them first maximizes coverage of newly heated
    regions. Using event recency ensures the simulator prioritizes hot
    frontiers over thermally stable, already-equilibrated lattice zones.
    """
    last_seq = {}
    for event in events:
        last_seq[event["node_id"]] = event["seq"]
    return sorted(nodes, key=lambda n: last_seq.get(n, 0))'''

new_priority = '''def compute_simulation_priority(nodes, vectors, events):
    """Determine simulation scheduling priority for lattice nodes.

    Priority is determined by total accumulated energy (vector sum).
    Nodes with lower energy sums are scheduled first to balance the lattice.
    """
    return sorted(nodes, key=lambda n: sum(vectors[n]))'''

analyzer_code = analyzer_code.replace(old_priority, new_priority)

with open(analyzer_path, "w") as f:
    f.write(analyzer_code)


# ============================================================
# Re-run the simulation with fixed code
# ============================================================

# Remove old output files
for f in ["/app/runtime/thermal_state.jsonl", "/app/runtime/thermal_summary.json"]:
    if os.path.exists(f):
        os.remove(f)

# Re-import and run with fixed modules
# Need to clear cached modules
for mod_name in list(sys.modules.keys()):
    if mod_name in ("diffusion_engine", "lattice_analyzer", "thermal_report",
                    "run_simulation", "log_parser"):
        del sys.modules[mod_name]

from run_simulation import run
run()
