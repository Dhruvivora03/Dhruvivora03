"""
Threat correlation orchestrator.

Parses the intrusion event log, processes all events through the threat
accumulator, and produces the segment state file and threat assessment report.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from intel_parser import parse_events, get_segment_ids
from threat_accumulator import SegmentThreat
from threat_report import write_report

STATE_PATH = os.path.join(os.path.dirname(__file__), "segment_state.jsonl")


def run_correlation():
    """Execute the full threat correlation pipeline."""
    # Parse events
    events = parse_events()
    segments = get_segment_ids(events)

    # Initialize threat trackers
    trackers = {}
    for sid in segments:
        trackers[sid] = SegmentThreat(sid, segments)

    # Process events
    for event in events:
        sid = event["segment_id"]
        eclass = event["event_class"]

        if eclass == "PROBE":
            trackers[sid].apply_probe()
        elif eclass == "BREACH":
            trackers[sid].apply_breach()
        elif eclass == "CORRELATE":
            trackers[sid].apply_correlate(event["payload"])

    # Extract final vectors
    vectors = {}
    for sid in segments:
        vectors[sid] = trackers[sid].get_vector()

    # Write state file
    state_lines = []
    for sid in sorted(segments):
        entry = {
            "segment_id": sid,
            "threat_vector": vectors[sid],
            "vector_sum": sum(vectors[sid]),
        }
        state_lines.append(entry)

    with open(STATE_PATH, "w") as fh:
        for line in state_lines:
            fh.write(json.dumps(line, sort_keys=True) + "\n")

    # Write threat assessment report
    write_report(segments, vectors, events)

    return state_lines


if __name__ == "__main__":
    results = run_correlation()
    print(f"Correlation complete. {len(results)} segments processed.")
    print(f"State written to: {STATE_PATH}")
