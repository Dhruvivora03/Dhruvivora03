"""
Control flow graph trace parser for abstract interpretation engine.

Reads the tilde-arrow separated dataflow trace and produces structured
operation records. Supports three operation types:
  TRANSFER: forward flow function application (+1 lattice height)
  WIDEN: widening operator application (+2 lattice height)
  JOIN: merge abstract states from predecessor program points
"""

import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "abstract_trace.log")


def parse_trace(path=None):
    """Parse the abstract interpretation trace into structured records.

    Returns list of dicts: step, point_id, operation, context.
    JOIN contexts are parsed into dicts; TRANSFER/WIDEN into strings.
    """
    if path is None:
        path = DATA_PATH

    operations = []
    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            parts = [p.strip() for p in line.split("~>")]
            if len(parts) != 4:
                continue

            step = int(parts[0])
            point_id = parts[1]
            operation = parts[2]
            raw_context = parts[3]

            if operation == "JOIN":
                state_str = raw_context.split("=", 1)[1]
                lattice_state = {}
                for pair in state_str.split(";"):
                    k, v = pair.split(":")
                    lattice_state[k] = int(v)
                context = lattice_state
            else:
                context = raw_context.split("=", 1)[1]

            operations.append({
                "step": step,
                "point_id": point_id,
                "operation": operation,
                "context": context,
            })

    return operations


def get_point_ids(operations):
    """Extract unique program point identifiers in discovery order."""
    seen = set()
    ids = []
    for op in operations:
        pid = op["point_id"]
        if pid not in seen:
            seen.add(pid)
            ids.append(pid)
    return ids
