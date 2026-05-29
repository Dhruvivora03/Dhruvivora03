"""
Orchestrator for GPU shader pipeline profiling system.

Coordinates the full profiling pipeline: reading the trace log, building
cycle vectors via the counter, analyzing the pipeline, and generating
the final report.
"""

import os
import sys
import json

# Ensure runtime directory is on path
sys.path.insert(0, os.path.dirname(__file__))

from log_reader import parse_profile_log, get_shader_ids
from cycle_counter import ShaderCycleTracker
from pipeline_analyzer import analyze_pipeline
from profiling_report import generate_report

RUNTIME_DIR = os.path.dirname(__file__)
STATE_FILE = os.path.join(RUNTIME_DIR, "profiler_state.jsonl")
REPORT_FILE = os.path.join(RUNTIME_DIR, "pipeline_report.json")


def build_cycle_vectors(events, shader_ids):
    """Process all events and build final cycle vectors."""
    trackers = {}
    for sid in shader_ids:
        trackers[sid] = ShaderCycleTracker(sid, shader_ids)

    for event in events:
        sid = event["shader_id"]
        etype = event["event_type"]
        details = event["details"]

        if etype == "SAMPLE":
            trackers[sid].apply_sample()
        elif etype == "BURST":
            trackers[sid].apply_burst()
        elif etype == "SYNC":
            trackers[sid].apply_sync(details["peer_state"])

    return trackers


def write_state(trackers, shader_ids, events):
    """Write profiler state to JSONL file."""
    with open(STATE_FILE, "w") as f:
        # Write shader states
        for sid in sorted(shader_ids):
            record = {
                "type": "shader_state",
                "shader_id": sid,
                "cycle_vector": trackers[sid].get_vector(),
                "own_cycles": trackers[sid].get_own_cycles(),
            }
            f.write(json.dumps(record) + "\n")

        # Write event summary
        event_counts = {}
        for e in events:
            sid = e["shader_id"]
            event_counts[sid] = event_counts.get(sid, 0) + 1

        summary = {
            "type": "event_summary",
            "total_events": len(events),
            "per_shader": event_counts,
        }
        f.write(json.dumps(summary) + "\n")


def main():
    """Run the full profiling pipeline."""
    # Step 1: Parse trace
    events = parse_profile_log()
    shader_ids = get_shader_ids(events)

    # Step 2: Build cycle vectors
    trackers = build_cycle_vectors(events, shader_ids)

    # Step 3: Write state file
    write_state(trackers, shader_ids, events)

    # Step 4: Extract vectors for analysis
    vectors = {}
    for sid in shader_ids:
        vectors[sid] = trackers[sid].get_vector()

    # Step 5: Generate report
    generate_report(shader_ids, vectors, events, REPORT_FILE)

    print(f"Profiling complete. State: {STATE_FILE}, Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
