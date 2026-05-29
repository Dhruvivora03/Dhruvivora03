"""
Simulation report writer for particle collision analysis.

Generates the final trajectory report in JSON format, including per-particle
state summaries, pair independence classifications, and a consistency digest
for validation of the full simulation pipeline.
"""

import json
import hashlib
from trajectory_analyzer import trajectories_are_independent, compute_harvesting_priority


def compute_digest(particles, vectors, independent_pairs, priority_order):
    """Compute 16-char hex digest of simulation results for validation.

    Combines particle vectors, pair classifications, and priority ordering
    into a single fingerprint that validates end-to-end correctness.
    """
    h = hashlib.sha256()

    # Include all vectors in sorted particle order
    for p in sorted(particles):
        vec_str = ",".join(str(v) for v in vectors[p])
        h.update(f"{p}:{vec_str}\n".encode())

    # Include independent pairs
    for p1, p2 in sorted(independent_pairs):
        h.update(f"indep:{p1},{p2}\n".encode())

    # Include priority order
    h.update(f"priority:{','.join(priority_order)}\n".encode())

    return h.hexdigest()[:16]


def generate_report(particles, vectors, events, output_path):
    """Generate full simulation report as JSON.

    Performs pair classification using trajectory independence check,
    computes harvesting priority, and writes comprehensive report.
    """
    # Classify all pairs
    independent_pairs = []
    dependent_pairs = []

    for i in range(len(particles)):
        for j in range(i + 1, len(particles)):
            vec_i = vectors[particles[i]]
            vec_j = vectors[particles[j]]
            if trajectories_are_independent(vec_i, vec_j):
                independent_pairs.append((particles[i], particles[j]))
            else:
                dependent_pairs.append((particles[i], particles[j]))

    # Compute priority
    priority_order = compute_harvesting_priority(particles, vectors, events)

    # Compute digest
    digest = compute_digest(particles, vectors, independent_pairs, priority_order)

    # Build report
    report = {
        "simulation_summary": {
            "particle_count": len(particles),
            "total_events": len(events),
            "particles": sorted(particles),
        },
        "momentum_state": {},
        "pair_classification": {
            "independent_pairs": [list(p) for p in independent_pairs],
            "dependent_pairs": [list(p) for p in dependent_pairs],
            "independent_count": len(independent_pairs),
            "total_pairs": len(independent_pairs) + len(dependent_pairs),
        },
        "harvesting_priority": priority_order,
        "validation": {
            "digest": digest,
        },
    }

    # Add per-particle state
    for p in sorted(particles):
        report["momentum_state"][p] = {
            "vector": vectors[p],
            "vector_sum": sum(vectors[p]),
        }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    return report
