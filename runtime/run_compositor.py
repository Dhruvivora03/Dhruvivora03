"""SDF ray marching compositor — pipeline entry point."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from scene_parser import parse_scene, get_prim_ids
from sdf_accumulator import PrimitiveSDF
from render_report import write_report

STATE_PATH = os.path.join(os.path.dirname(__file__), "sdf_state.jsonl")


def run_compositor():
    operations = parse_scene()
    prims = get_prim_ids(operations)
    trackers = {}
    for pid in prims:
        trackers[pid] = PrimitiveSDF(pid, prims)
    for op in operations:
        pid = op["prim_id"]
        otype = op["op_type"]
        if otype == "MARCH":
            trackers[pid].apply_march()
        elif otype == "INTERSECT":
            trackers[pid].apply_intersect()
        elif otype == "BLEND":
            trackers[pid].apply_blend(op["params"])
    vectors = {}
    for pid in prims:
        vectors[pid] = trackers[pid].get_vector()
    state_lines = []
    for pid in sorted(prims):
        entry = {"prim_id": pid, "sdf_vector": vectors[pid], "vector_sum": sum(vectors[pid])}
        state_lines.append(entry)
    with open(STATE_PATH, "w") as fh:
        for line in state_lines:
            fh.write(json.dumps(line, sort_keys=True) + "\n")
    write_report(prims, vectors, operations)
    return state_lines


if __name__ == "__main__":
    results = run_compositor()
    print(f"Compositor complete. {len(results)} primitives processed.")
    print(f"State written to: {STATE_PATH}")
