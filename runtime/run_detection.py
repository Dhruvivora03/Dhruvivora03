"""
Network intrusion detection pipeline orchestrator.
Coordinates event parsing, threat propagation modeling, segment
classification, and report generation.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from event_parser import load_threat_events, extract_segments
from propagation_model import (
    initialize_threat_state, process_scan, process_exploit,
    process_lateral, get_threat_vector,
)
from segment_classifier import classify_network
from detection_report import generate_findings, generate_summary


def run():
    """Execute the full intrusion detection pipeline."""
    # Phase 1: Load threat event stream
    events = load_threat_events()
    segments = extract_segments(events)

    # Phase 2: Initialize threat propagation state
    threat_state = initialize_threat_state(segments)

    # Phase 3: Process each event through the propagation model
    for ev in events:
        seg = ev["segment"]
        if ev["action"] == "SCAN":
            process_scan(threat_state, seg)
        elif ev["action"] == "EXPLOIT":
            process_exploit(threat_state, seg)
        elif ev["action"] == "LATERAL":
            process_lateral(threat_state, seg, ev["payload"])

    # Phase 4: Extract final threat vectors
    threat_vectors = {}
    for seg in segments:
        threat_vectors[seg] = get_threat_vector(threat_state, seg)

    # Phase 5: Classify network segments
    classification = classify_network(segments, threat_vectors, events)

    # Phase 6: Generate detection reports
    findings = generate_findings(segments, threat_vectors, events, classification)
    summary = generate_summary(findings, classification)

    print(f"Detection complete. Fingerprint: {summary['fingerprint']}")
    print(f"Segments: {summary['segment_count']}, Isolation pairs: {summary['isolation_pair_count']}")
    print(f"Triage order: {summary['triage_order']}")

    return summary


if __name__ == "__main__":
    run()
