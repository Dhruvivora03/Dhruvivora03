"""
Intrusion detection report generator.
Produces the final JSONL findings file and JSON summary combining
threat state observations with network classification results.
"""

import json
import hashlib
import os

from segment_classifier import can_isolate_segments

OUTPUT_DIR = os.path.dirname(__file__)
FINDINGS_FILE = os.path.join(OUTPUT_DIR, "detection_findings.jsonl")
SUMMARY_FILE = os.path.join(OUTPUT_DIR, "detection_summary.json")


def generate_findings(segments, threat_vectors, events, classification):
    """Write per-segment findings to JSONL file."""
    findings = []
    ordered_segs = sorted(segments)

    for seg in ordered_segs:
        vec = threat_vectors[seg]
        # Determine which segments can be isolated from this one
        isolatable = []
        for other in ordered_segs:
            if other == seg:
                continue
            if can_isolate_segments(vec, threat_vectors[other]):
                isolatable.append(other)

        finding = {
            "segment_id": seg,
            "threat_vector": vec,
            "threat_total": sum(vec),
            "isolatable_from": isolatable,
            "triage_rank": classification["triage_order"].index(seg),
        }
        findings.append(finding)

    with open(FINDINGS_FILE, "w") as fh:
        for rec in findings:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")

    return findings


def compute_fingerprint(findings):
    """Compute a 16-character hex fingerprint of the full findings state."""
    serialized = json.dumps(findings, sort_keys=True)
    return hashlib.md5(serialized.encode()).hexdigest()[:16]


def generate_summary(findings, classification):
    """Write the detection summary report with fingerprint and metrics."""
    fingerprint = compute_fingerprint(findings)

    summary = {
        "fingerprint": fingerprint,
        "segment_count": len(findings),
        "isolation_pair_count": len(classification["isolation_pairs"]),
        "isolation_pairs": [list(p) for p in classification["isolation_pairs"]],
        "triage_order": classification["triage_order"],
        "aggregate_threat": sum(f["threat_total"] for f in findings),
    }

    with open(SUMMARY_FILE, "w") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True)

    return summary
