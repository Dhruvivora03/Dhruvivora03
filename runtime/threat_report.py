"""
Threat correlation report writer.

Generates the final threat assessment report by combining segment threat
state data with correlation analysis results. The report includes per-segment
threat vectors, isolated pair classifications, and the computed triage ordering.
"""

import json
import hashlib
import os

from correlation_analyzer import analyze_threats

REPORT_PATH = os.path.join(os.path.dirname(__file__), "threat_assessment.jsonl")


def compute_digest(report_lines):
    """Compute a 16-character hex digest of the report content."""
    content = "\n".join(json.dumps(line, sort_keys=True) for line in report_lines)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def write_report(segments, vectors, events, output_path=None):
    """Write the threat assessment report combining state and analysis.

    The report is a JSONL file with:
    - One line per segment: segment_id, threat_vector, vector_sum
    - Analysis line: isolated_pairs, triage_order
    - Digest line: fingerprint hash for integrity verification
    """
    if output_path is None:
        output_path = REPORT_PATH

    # Run threat correlation analysis
    analysis = analyze_threats(segments, vectors, events)

    report_lines = []

    # Segment state entries
    for sid in sorted(segments):
        vec = vectors[sid]
        report_lines.append({
            "type": "segment_state",
            "segment_id": sid,
            "threat_vector": vec,
            "vector_sum": sum(vec),
        })

    # Analysis entry
    report_lines.append({
        "type": "correlation_analysis",
        "isolated_pairs": [list(p) for p in analysis["isolated_pairs"]],
        "isolated_count": len(analysis["isolated_pairs"]),
        "triage_order": analysis["triage_order"],
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
