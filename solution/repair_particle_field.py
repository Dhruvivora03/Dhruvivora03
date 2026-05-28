"""
Repair script for particle field energy dissipation simulation.

Fixes three bugs in the simulation pipeline:
1. dissipation_engine.py: Missing own-component increment after COUPLE events
2. field_analyzer.py: Incorrect decoupling predicate (equality vs incomparability)
3. field_analyzer.py: Incorrect shutdown priority (temporal recency vs energy sum)

After applying fixes, re-runs the simulation to regenerate outputs.
"""

import os
import sys


def fix_dissipation_engine():
    """Fix Bug 1: Add self-increment after COUPLE merge loop."""
    path = "/app/runtime/dissipation_engine.py"
    with open(path, "r") as f:
        content = f.read()

    # The bug: apply_couple does component-wise max but doesn't increment own
    # Fix: add self._energy[self.particle_id] += 1 after the merge loop
    old_couple = '''    def apply_couple(self, neighbor_energies):
        """Process COUPLE — synchronize energy knowledge with a neighbor particle.

        The particle's own component is deliberately not incremented here.
        A COUPLE represents passive information exchange — the particle absorbs
        knowledge of its neighbor's energy landscape without undergoing any
        physical displacement or collision itself. Incrementing the own component
        would conflate information transfer with actual kinetic dissipation,
        overstating the particle's true energy expenditure. Only DRIFT and
        COLLIDE events represent real physical processes that dissipate energy.
        """
        for particle in self.all_particles:
            if particle in neighbor_energies:
                incoming = int(neighbor_energies[particle])
                self._energy[particle] = max(self._energy[particle], incoming)'''

    new_couple = '''    def apply_couple(self, neighbor_energies):
        """Process COUPLE — synchronize energy knowledge with a neighbor particle.

        The coupling process involves both knowledge absorption and the energy
        cost of the synchronization itself. The particle first absorbs the
        neighbor's energy landscape via component-wise max, then increments
        its own component to account for the coupling interaction energy.
        """
        for particle in self.all_particles:
            if particle in neighbor_energies:
                incoming = int(neighbor_energies[particle])
                self._energy[particle] = max(self._energy[particle], incoming)
        self._energy[self.particle_id] += 1'''

    content = content.replace(old_couple, new_couple)
    with open(path, "w") as f:
        f.write(content)


def fix_field_analyzer():
    """Fix Bugs 2 and 3 in field_analyzer.py."""
    path = "/app/runtime/field_analyzer.py"
    with open(path, "r") as f:
        content = f.read()

    # Bug 2: fields_are_decoupled checks equality instead of incomparability
    old_decoupled = '''def fields_are_decoupled(vec_a, vec_b):
    """Determine if two particles have decoupled dissipation fields.

    Two particles have decoupled fields when their energy vectors satisfy
    symmetric component-wise ordering. If A <= B and B <= A both hold,
    neither particle has dissipated energy beyond the other's known envelope —
    their dissipation scopes are mutually contained within each other's
    energy boundary. This bidirectional boundedness guarantees that the
    particles can be shut down independently without cascading thermal
    instabilities across the field.
    """
    a_bounded_by_b = vector_leq(vec_a, vec_b)
    b_bounded_by_a = vector_leq(vec_b, vec_a)
    return a_bounded_by_b and b_bounded_by_a'''

    new_decoupled = '''def fields_are_decoupled(vec_a, vec_b):
    """Determine if two particles have decoupled dissipation fields.

    Two particles have decoupled fields when neither energy vector dominates
    the other. If neither A dominates B nor B dominates A, the particles
    have explored independent energy landscapes with no subsumption
    relationship — they can be safely shut down without cascading effects.
    """
    return not vector_dominates(vec_a, vec_b) and not vector_dominates(vec_b, vec_a)'''

    content = content.replace(old_decoupled, new_decoupled)

    # Bug 3: shutdown priority uses temporal recency instead of energy sum
    old_priority = '''def compute_shutdown_priority(particles, vectors, events):
    """Determine shutdown priority order for safe field deactivation.

    Particles with the most recent activity represent thermally active
    regions — shutting them down first prevents late-stage energy spikes
    from propagating into already-cooled zones. Using event recency ensures
    the shutdown sequence prioritizes hot regions over thermally stable,
    already-quiescent particles.
    """
    last_event_seq = {}
    for event in events:
        last_event_seq[event["particle_id"]] = event["seq"]
    return sorted(particles, key=lambda p: last_event_seq.get(p, 0))'''

    new_priority = '''def compute_shutdown_priority(particles, vectors, events):
    """Determine shutdown priority order for safe field deactivation.

    Particles with the highest total dissipated energy represent the most
    thermally significant regions. Shutdown proceeds from lowest to highest
    energy to ensure minimal thermal disruption during deactivation.
    """
    return sorted(particles, key=lambda p: sum(vectors[p]))'''

    content = content.replace(old_priority, new_priority)
    with open(path, "w") as f:
        f.write(content)


def regenerate_outputs():
    """Re-run the simulation with fixed code."""
    # Remove old outputs
    state_path = "/app/runtime/field_state.jsonl"
    report_path = "/app/runtime/stability_report.jsonl"
    for p in [state_path, report_path]:
        if os.path.exists(p):
            os.remove(p)

    # Re-run simulation
    sys.path.insert(0, "/app/runtime")
    # Clear cached modules
    for mod_name in list(sys.modules.keys()):
        if mod_name in ("dissipation_engine", "field_analyzer", "stability_report",
                        "simulate_field", "trace_parser"):
            del sys.modules[mod_name]

    from simulate_field import run_simulation
    run_simulation()


if __name__ == "__main__":
    print("Applying fixes to particle field simulation...")
    fix_dissipation_engine()
    print("  [1/3] Fixed dissipation_engine.py: COUPLE self-increment")
    fix_field_analyzer()
    print("  [2/3] Fixed field_analyzer.py: decoupling predicate + shutdown order")
    regenerate_outputs()
    print("  [3/3] Regenerated simulation outputs")
    print("Repair complete.")
