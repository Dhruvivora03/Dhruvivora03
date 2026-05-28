"""
Stability report writer.

Generates the final stability report by combining energy state data with
field analysis results. The report includes per-particle energy vectors,
decoupled pair classifications, and the computed shutdown ordering.
"""

import json
import hashlib
import os

from field_analyzer import analyze_field

REPORT_PATH = os.path.join(os.path.dirname(__file__), "stability_report.jsonl")


def compute_digest(report_lines):
    """Compute a 16-character hex digest of the report content."""
    content = "\n".join(json.dumps(line, sort_keys=True) for line in report_lines)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def write_report(particles, vectors, events, output_path=None):
    """Write the stability report combining state and analysis.

    The report is a JSONL file with:
    - One line per particle: particle_id, energy_vector, vector_sum
    - Analysis line: decoupled_pairs, shutdown_order
    - Digest line: fingerprint hash for integrity verification
    """
    if output_path is None:
        output_path = REPORT_PATH

    # Run field analysis
    analysis = analyze_field(particles, vectors, events)

    report_lines = []

    # Particle state entries
    for pid in sorted(particles):
        vec = vectors[pid]
        report_lines.append({
            "type": "particle_state",
            "particle_id": pid,
            "energy_vector": vec,
            "vector_sum": sum(vec),
        })

    # Analysis entry
    report_lines.append({
        "type": "field_analysis",
        "decoupled_pairs": [list(p) for p in analysis["decoupled_pairs"]],
        "decoupled_count": len(analysis["decoupled_pairs"]),
        "shutdown_order": analysis["shutdown_order"],
    })

    # Digest entry
    digest = compute_digest(report_lines)
    report_lines.append({
        "type": "digest",
        "fingerprint": digest,
    })

    # Write JSONL
    with open(output_path, "w") as fh:
        for line in report_lines:
            fh.write(json.dumps(line, sort_keys=True) + "\n")

    return report_lines
