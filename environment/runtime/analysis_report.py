"""Analysis report writer for abstract interpretation results."""

import json
import hashlib
import os

from fixpoint_analyzer import analyze_convergence

REPORT_PATH = os.path.join(os.path.dirname(__file__), "analysis_report.jsonl")


def compute_digest(report_lines):
    content = "\n".join(json.dumps(line, sort_keys=True) for line in report_lines)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def write_report(points, vectors, operations, output_path=None):
    if output_path is None:
        output_path = REPORT_PATH
    analysis = analyze_convergence(points, vectors, operations)
    report_lines = []
    for pid in sorted(points):
        vec = vectors[pid]
        report_lines.append({"type": "point_state", "point_id": pid, "lattice_vector": vec, "vector_sum": sum(vec)})
    report_lines.append({"type": "convergence_analysis", "converged_pairs": [list(p) for p in analysis["converged_pairs"]], "converged_count": len(analysis["converged_pairs"]), "worklist_order": analysis["worklist_order"]})
    digest = compute_digest(report_lines)
    report_lines.append({"type": "digest", "fingerprint": digest})
    with open(output_path, "w") as fh:
        for line in report_lines:
            fh.write(json.dumps(line, sort_keys=True) + "\n")
    return report_lines
