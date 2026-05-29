"""
Orchestrator for particle collision simulation pipeline.

Coordinates the full simulation: parsing the collision trace, building
momentum vectors via the tracker, analyzing trajectories, and generating
the final report.
"""

import os
import sys
import json

# Ensure runtime directory is on path
sys.path.insert(0, os.path.dirname(__file__))

from trace_parser import parse_trace, get_particle_ids
from momentum_tracker import ParticleMomentum
from trajectory_analyzer import analyze_trajectories
from simulation_report import generate_report

RUNTIME_DIR = os.path.dirname(__file__)
STATE_FILE = os.path.join(RUNTIME_DIR, "simulation_state.jsonl")
REPORT_FILE = os.path.join(RUNTIME_DIR, "trajectory_report.json")


def build_momentum_vectors(events, particle_ids):
    """Process all events and build final momentum vectors."""
    trackers = {}
    for pid in particle_ids:
        trackers[pid] = ParticleMomentum(pid, particle_ids)

    for event in events:
        pid = event["particle_id"]
        etype = event["event_type"]
        details = event["details"]

        if etype == "DRIFT":
            trackers[pid].apply_drift()
        elif etype == "THRUST":
            trackers[pid].apply_thrust()
        elif etype == "COLLIDE":
            trackers[pid].apply_collide(details["peer_state"])

    return trackers


def write_state(trackers, particle_ids, events):
    """Write simulation state to JSONL file."""
    with open(STATE_FILE, "w") as f:
        # Write particle states
        for pid in sorted(particle_ids):
            record = {
                "type": "particle_state",
                "particle_id": pid,
                "momentum_vector": trackers[pid].get_vector(),
                "own_momentum": trackers[pid].get_own_momentum(),
            }
            f.write(json.dumps(record) + "\n")

        # Write event summary
        event_counts = {}
        for e in events:
            pid = e["particle_id"]
            event_counts[pid] = event_counts.get(pid, 0) + 1

        summary = {
            "type": "event_summary",
            "total_events": len(events),
            "per_particle": event_counts,
        }
        f.write(json.dumps(summary) + "\n")


def main():
    """Run the full simulation pipeline."""
    # Step 1: Parse trace
    events = parse_trace()
    particle_ids = get_particle_ids(events)

    # Step 2: Build momentum vectors
    trackers = build_momentum_vectors(events, particle_ids)

    # Step 3: Write state file
    write_state(trackers, particle_ids, events)

    # Step 4: Extract vectors for analysis
    vectors = {}
    for pid in particle_ids:
        vectors[pid] = trackers[pid].get_vector()

    # Step 5: Generate report
    generate_report(particle_ids, vectors, events, REPORT_FILE)

    print(f"Simulation complete. State: {STATE_FILE}, Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
