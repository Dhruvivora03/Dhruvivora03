"""
Field simulation orchestrator.

Parses the particle trace log, processes all events through the dissipation
engine, and produces the field state file and stability report.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from trace_parser import parse_trace, get_particle_ids
from dissipation_engine import ParticleEnergy
from stability_report import write_report

STATE_PATH = os.path.join(os.path.dirname(__file__), "field_state.jsonl")


def run_simulation():
    """Execute the full particle field simulation pipeline."""
    # Parse events
    events = parse_trace()
    particles = get_particle_ids(events)

    # Initialize energy trackers
    trackers = {}
    for pid in particles:
        trackers[pid] = ParticleEnergy(pid, particles)

    # Process events
    for event in events:
        pid = event["particle_id"]
        etype = event["event_type"]

        if etype == "DRIFT":
            trackers[pid].apply_drift()
        elif etype == "COLLIDE":
            trackers[pid].apply_collide()
        elif etype == "COUPLE":
            trackers[pid].apply_couple(event["detail"])

    # Extract final vectors
    vectors = {}
    for pid in particles:
        vectors[pid] = trackers[pid].get_vector()

    # Write state file
    state_lines = []
    for pid in sorted(particles):
        entry = {
            "particle_id": pid,
            "energy_vector": vectors[pid],
            "vector_sum": sum(vectors[pid]),
        }
        state_lines.append(entry)

    with open(STATE_PATH, "w") as fh:
        for line in state_lines:
            fh.write(json.dumps(line, sort_keys=True) + "\n")

    # Write stability report
    write_report(particles, vectors, events)

    return state_lines


if __name__ == "__main__":
    results = run_simulation()
    print(f"Simulation complete. {len(results)} particles processed.")
    print(f"State written to: {STATE_PATH}")
