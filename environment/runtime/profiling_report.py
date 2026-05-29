"""
Profiling report writer for GPU shader pipeline analysis.

Generates the final profiling report in JSON format, including per-shader
cycle summaries, stage disjointness classifications, and a consistency
digest for validation of the full profiling pipeline.
"""

import json
import hashlib
from pipeline_analyzer import stages_are_disjoint, compute_scheduling_priority


def compute_digest(shaders, vectors, disjoint_pairs, priority_order):
    """Compute 16-char hex digest of profiling results for validation.

    Combines shader vectors, pair classifications, and priority ordering
    into a single fingerprint that validates end-to-end correctness.
    """
    h = hashlib.sha256()

    # Include all vectors in sorted shader order
    for s in sorted(shaders):
        vec_str = ",".join(str(v) for v in vectors[s])
        h.update(f"{s}:{vec_str}\n".encode())

    # Include disjoint pairs
    for s1, s2 in sorted(disjoint_pairs):
        h.update(f"disjoint:{s1},{s2}\n".encode())

    # Include priority order
    h.update(f"priority:{','.join(priority_order)}\n".encode())

    return h.hexdigest()[:16]


def generate_report(shaders, vectors, events, output_path):
    """Generate full profiling report as JSON.

    Performs pair classification using stage disjointness check,
    computes scheduling priority, and writes comprehensive report.
    """
    # Classify all pairs
    disjoint_pairs = []
    coupled_pairs = []

    for i in range(len(shaders)):
        for j in range(i + 1, len(shaders)):
            vec_i = vectors[shaders[i]]
            vec_j = vectors[shaders[j]]
            if stages_are_disjoint(vec_i, vec_j):
                disjoint_pairs.append((shaders[i], shaders[j]))
            else:
                coupled_pairs.append((shaders[i], shaders[j]))

    # Compute priority
    priority_order = compute_scheduling_priority(shaders, vectors, events)

    # Compute digest
    digest = compute_digest(shaders, vectors, disjoint_pairs, priority_order)

    # Build report
    report = {
        "profiling_summary": {
            "shader_count": len(shaders),
            "total_events": len(events),
            "shaders": sorted(shaders),
        },
        "cycle_state": {},
        "pair_classification": {
            "disjoint_pairs": [list(p) for p in disjoint_pairs],
            "coupled_pairs": [list(p) for p in coupled_pairs],
            "disjoint_count": len(disjoint_pairs),
            "total_pairs": len(disjoint_pairs) + len(coupled_pairs),
        },
        "scheduling_priority": priority_order,
        "validation": {
            "digest": digest,
        },
    }

    # Add per-shader state
    for s in sorted(shaders):
        report["cycle_state"][s] = {
            "vector": vectors[s],
            "vector_sum": sum(vectors[s]),
        }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    return report
