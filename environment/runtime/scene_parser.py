"""
Scene trace parser for SDF ray marching compositor.

Reads the hash-separated scene composition log and produces structured
operation records. Three operation types:
  MARCH: single ray step advancing distance (+1)
  INTERSECT: CSG intersection tightening distance (+2)
  BLEND: smooth blending with neighbor primitive's SDF field
"""

import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "scene_trace.log")


def parse_scene(path=None):
    if path is None:
        path = DATA_PATH
    operations = []
    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            parts = [p.strip() for p in line.split("#")]
            if len(parts) != 4:
                continue
            step = int(parts[0])
            prim_id = parts[1]
            op_type = parts[2]
            raw_params = parts[3]
            if op_type == "BLEND":
                state_str = raw_params.split("=", 1)[1]
                sdf_state = {}
                for pair in state_str.split(";"):
                    k, v = pair.split(":")
                    sdf_state[k] = int(v)
                params = sdf_state
            else:
                params = float(raw_params.split("=", 1)[1])
            operations.append({
                "step": step,
                "prim_id": prim_id,
                "op_type": op_type,
                "params": params,
            })
    return operations


def get_prim_ids(operations):
    seen = set()
    ids = []
    for op in operations:
        pid = op["prim_id"]
        if pid not in seen:
            seen.add(pid)
            ids.append(pid)
    return ids
