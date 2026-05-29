"""
Threat assessment report writer.

Combines segment state data with correlation analysis to produce the
final JSONL threat assessment report including integrity digest.
"""

import json
import hashlib
import os

from correlation_analyzer import analyze_threats

REPORT_PATH = os.path.join(os.path.dirname(__file__), "threat_assessment.jsonl")


def compute_digest(report_lines):
    """Compute 16-char hex integrity digest over report content."""
    content = "\n".join(json.dumps(line, sort_keys=True) for line in report_lines)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def write_report(segments, vectors, events, output_path=None):
    """Write the threat assessment JSONL report."""
    if output_path is None:
        output_path = REPORT_PATH

    analysis = analyze_threats(segments, vectors, events)

    report_lines = []
    for sid in sorted(segments):
        vec = vectors[sid]
        report_lines.append({
            "type": "segment_state",
            "segment_id": sid,
            "threat_vector": vec,
            "vector_sum": sum(vec),
        })

    report_lines.append({
        "type": "correlation_analysis",
        "isolated_pairs": [list(p) for p in analysis["isolated_pairs"]],
        "isolated_count": len(analysis["isolated_pairs"]),
        "triage_order": analysis["triage_order"],
    })

    digest = compute_digest(report_lines)
    report_lines.append({
        "type": "digest",
        "fingerprint": digest,
    })

    with open(output_path, "w") as fh:
        for line in report_lines:
            fh.write(json.dumps(line, sort_keys=True) + "\n")

    return report_lines
