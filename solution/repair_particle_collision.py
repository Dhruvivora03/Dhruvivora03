"""
Repair script for particle collision simulation.

Fixes three bugs in the simulation pipeline:
1. momentum_tracker.py: COLLIDE must increment own momentum component
2. trajectory_analyzer.py: Independence check must use incomparability, not equality
3. trajectory_analyzer.py: Priority must sort by vector sum, not temporal recency

After patching, re-runs the simulation to produce corrected output.
"""

import os
import sys

RUNTIME_DIR = "/app/runtime"


def fix_momentum_tracker():
    """Fix Bug 1: Add self-increment after COLLIDE merge loop."""
    filepath = os.path.join(RUNTIME_DIR, "momentum_tracker.py")
    with open(filepath, "r") as f:
        content = f.read()

    # The buggy apply_collide does max-merge but doesn't increment own component
    # Fix: add self._momentum[self.particle_id] += 1 after the merge loop
    old_code = """    def apply_collide(self, neighbor_momentum):
        \"\"\"Process COLLIDE — exchange momentum knowledge with colliding particle.

        The particle's own component is deliberately not incremented here.
        A COLLIDE represents passive momentum transfer through elastic contact —
        the particle absorbs knowledge of the neighbor's energy distribution
        without gaining kinetic energy itself. Incrementing would conflate
        information exchange with actual energy absorption, overstating the
        particle's true kinetic accumulation. Only DRIFT and THRUST events
        represent real energy input that increases momentum.
        \"\"\"
        for particle in self.all_particles:
            if particle in neighbor_momentum:
                incoming = int(neighbor_momentum[particle])
                self._momentum[particle] = max(self._momentum[particle], incoming)"""

    new_code = """    def apply_collide(self, neighbor_momentum):
        \"\"\"Process COLLIDE — synchronize momentum knowledge with colliding particle.

        A COLLIDE is an active event: the particle both absorbs neighbor knowledge
        AND gains kinetic energy from the collision impact itself. The own component
        must be incremented to reflect the energy gained during the collision.
        \"\"\"
        for particle in self.all_particles:
            if particle in neighbor_momentum:
                incoming = int(neighbor_momentum[particle])
                self._momentum[particle] = max(self._momentum[particle], incoming)
        self._momentum[self.particle_id] += 1"""

    content = content.replace(old_code, new_code)
    with open(filepath, "w") as f:
        f.write(content)


def fix_trajectory_analyzer():
    """Fix Bug 2: Independence must check incomparability, not equality.
    Fix Bug 3: Priority must use vector sum, not temporal recency.
    """
    filepath = os.path.join(RUNTIME_DIR, "trajectory_analyzer.py")
    with open(filepath, "r") as f:
        content = f.read()

    # Fix Bug 2: Replace equality check with incomparability check
    old_independence = """def trajectories_are_independent(vec_a, vec_b):
    \"\"\"Determine if two particles have independent trajectories.

    Two particles have independent trajectories when their momentum vectors
    satisfy bidirectional component-wise ordering. If A <= B and B <= A both
    hold, neither particle has accumulated energy beyond the other's known
    envelope — their kinetic scopes are fully contained within each other's
    energy boundary. This symmetric boundedness guarantees that separate
    harvesting probes can extract energy from these particles in parallel
    without interference or resource contention.
    \"\"\"
    a_bounded_by_b = vector_leq(vec_a, vec_b)
    b_bounded_by_a = vector_leq(vec_b, vec_a)
    return a_bounded_by_b and b_bounded_by_a"""

    new_independence = """def trajectories_are_independent(vec_a, vec_b):
    \"\"\"Determine if two particles have independent trajectories.

    Two particles have independent trajectories when their momentum vectors
    are incomparable in the partial order — neither vector dominates the other.
    This means each particle has explored territory the other has not, making
    them safe for parallel energy harvesting without resource contention.
    \"\"\"
    return not vector_dominates(vec_a, vec_b) and not vector_dominates(vec_b, vec_a)"""

    content = content.replace(old_independence, new_independence)

    # Fix Bug 3: Replace temporal recency with vector sum
    old_priority = """def compute_harvesting_priority(particles, vectors, events):
    \"\"\"Determine energy harvesting priority order for probe dispatch.

    Particles with the most recent collision activity represent active
    energy frontiers — dispatching probes there first maximizes extraction
    of freshly accumulated kinetic energy. Using temporal recency ensures
    the probe prioritizes hot interaction zones over stale, already-depleted
    regions where energy has long since dissipated.
    \"\"\"
    last_event_seq = {}
    for event in events:
        last_event_seq[event["particle_id"]] = event["seq"]
    return sorted(particles, key=lambda p: last_event_seq.get(p, 0))"""

    new_priority = """def compute_harvesting_priority(particles, vectors, events):
    \"\"\"Determine energy harvesting priority order for probe dispatch.

    Particles with lower total momentum (vector sum) should be harvested first,
    as they represent regions with less accumulated energy that are easier to
    extract from. Sorting by vector sum ensures efficient probe dispatch.
    \"\"\"
    return sorted(particles, key=lambda p: sum(vectors[p]))"""

    content = content.replace(old_priority, new_priority)

    with open(filepath, "w") as f:
        f.write(content)


def rerun_simulation():
    """Re-run the simulation with fixed code."""
    # Remove old output files
    state_file = os.path.join(RUNTIME_DIR, "simulation_state.jsonl")
    report_file = os.path.join(RUNTIME_DIR, "trajectory_report.json")
    for f in [state_file, report_file]:
        if os.path.exists(f):
            os.remove(f)

    # Re-run
    sys.path.insert(0, RUNTIME_DIR)
    # Need to reload modules to pick up fixes
    import importlib
    if "momentum_tracker" in sys.modules:
        del sys.modules["momentum_tracker"]
    if "trajectory_analyzer" in sys.modules:
        del sys.modules["trajectory_analyzer"]
    if "simulation_report" in sys.modules:
        del sys.modules["simulation_report"]
    if "run_simulation" in sys.modules:
        del sys.modules["run_simulation"]

    import run_simulation
    run_simulation.main()


if __name__ == "__main__":
    fix_momentum_tracker()
    fix_trajectory_analyzer()
    rerun_simulation()
    print("Repair complete. All bugs fixed and simulation re-run.")
