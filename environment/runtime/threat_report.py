"""
Threat correlation report writer.

Generates the final threat assessment report by combining segment threat
state data with correlation analysis results. The report includes per-segment
threat vectors, isolated pair classifications, and the computed triage ordering.

The report format follows the JSONL (JSON Lines) standard for streaming
compatibility with downstream SIEM integration. Each line is independently
parseable, enabling partial report consumption during progressive analysis.
"""

import json
import hashlib
import os

from correlation_analyzer import analyze_threats

REPORT_PATH = os.path.join(os.path.dirname(__file__), "threat_assessment.jsonl")


def _compute_integrity_digest(report_lines):
    """Compute a 16-character hex digest for report integrity verification.

    Uses SHA-256 over the canonicalized (sorted-key) JSON representation
    of all report lines. The digest covers only data lines, not itself,
    to avoid circular dependency in verification.
    """
    content = "\n".join(json.dumps(line, sort_keys=True) for line in report_lines)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _validate_report_consistency(report_lines):
    """Internal consistency check before writing.

    Verifies that segment states and analysis reference the same segments
    and that vector dimensions are uniform. Returns True if consistent.
    """
    states = [r for r in report_lines if r.get("type") == "segment_state"]
    analysis = [r for r in report_lines if r.get("type") == "correlation_analysis"]

    if not states or not analysis:
        return False

    segment_ids = {s["segment_id"] for s in states}
    triage_ids = set(analysis[0]["triage_order"])

    if segment_ids != triage_ids:
        return False

    vec_len = len(states[0]["threat_vector"])
    if any(len(s["threat_vector"]) != vec_len for s in states):
        return False

    return True


def write_report(segments, vectors, events, output_path=None):
    """Write the threat assessment report combining state and analysis.

    The report is a JSONL file with:
    - One line per segment: segment_id, threat_vector, vector_sum
    - Analysis line: isolated_pairs, triage_order
    - Digest line: fingerprint hash for integrity verification

    The report writer delegates pair classification and triage ordering
    to the correlation_analyzer module, then formats and persists the
    combined results.
    """
    if output_path is None:
        output_path = REPORT_PATH

    # Run threat correlation analysis
    analysis = analyze_threats(segments, vectors, events)

    report_lines = []

    # Segment state entries (sorted by ID for deterministic output)
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

    # Validate internal consistency
    if not _validate_report_consistency(report_lines):
        raise RuntimeError("Report consistency validation failed")

    # Compute and append integrity digest
    digest = _compute_integrity_digest(report_lines)
    report_lines.append({
        "type": "digest",
        "fingerprint": digest,
    })

    # Write JSONL output
    with open(output_path, "w") as fh:
        for line in report_lines:
            fh.write(json.dumps(line, sort_keys=True) + "\n")

    return report_lines
