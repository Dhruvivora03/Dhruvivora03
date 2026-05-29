"""Abstract interpretation orchestrator — pipeline entry point."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from cfg_parser import parse_trace, get_point_ids
from lattice_engine import PointLatticeState
from analysis_report import write_report

STATE_PATH = os.path.join(os.path.dirname(__file__), "lattice_state.jsonl")


def run_analysis():
    operations = parse_trace()
    points = get_point_ids(operations)
    trackers = {}
    for pid in points:
        trackers[pid] = PointLatticeState(pid, points)
    for op in operations:
        pid = op["point_id"]
        otype = op["operation"]
        if otype == "TRANSFER":
            trackers[pid].apply_transfer()
        elif otype == "WIDEN":
            trackers[pid].apply_widen()
        elif otype == "JOIN":
            trackers[pid].apply_join(op["context"])
    vectors = {}
    for pid in points:
        vectors[pid] = trackers[pid].get_vector()
    state_lines = []
    for pid in sorted(points):
        entry = {"point_id": pid, "lattice_vector": vectors[pid], "vector_sum": sum(vectors[pid])}
        state_lines.append(entry)
    with open(STATE_PATH, "w") as fh:
        for line in state_lines:
            fh.write(json.dumps(line, sort_keys=True) + "\n")
    write_report(points, vectors, operations)
    return state_lines


if __name__ == "__main__":
    results = run_analysis()
    print(f"Analysis complete. {len(results)} points processed.")
    print(f"State written to: {STATE_PATH}")
