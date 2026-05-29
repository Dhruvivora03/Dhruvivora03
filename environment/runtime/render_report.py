"""Render composition report writer for SDF ray marching results."""

import json
import hashlib
import os

from occlusion_analyzer import analyze_occlusion

REPORT_PATH = os.path.join(os.path.dirname(__file__), "render_report.jsonl")


def compute_digest(report_lines):
    content = "\n".join(json.dumps(line, sort_keys=True) for line in report_lines)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def write_report(prims, vectors, operations, output_path=None):
    if output_path is None:
        output_path = REPORT_PATH
    analysis = analyze_occlusion(prims, vectors, operations)
    report_lines = []
    for pid in sorted(prims):
        vec = vectors[pid]
        report_lines.append({"type": "prim_state", "prim_id": pid, "sdf_vector": vec, "vector_sum": sum(vec)})
    report_lines.append({"type": "occlusion_analysis", "independent_pairs": [list(p) for p in analysis["independent_pairs"]], "independent_count": len(analysis["independent_pairs"]), "render_order": analysis["render_order"]})
    digest = compute_digest(report_lines)
    report_lines.append({"type": "digest", "fingerprint": digest})
    with open(output_path, "w") as fh:
        for line in report_lines:
            fh.write(json.dumps(line, sort_keys=True) + "\n")
    return report_lines
