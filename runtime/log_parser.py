"""
Thermal log parser.
Reads the arrow-separated trace file and produces structured event records
for downstream simulation components.
"""

import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "thermal_log.txt")


def parse_thermal_log(path=None):
    """Parse the thermal diffusion trace log into event records.

    Returns a list of dicts with keys: seq, node_id, event_type, detail
    For EQUILIBRATE events, detail contains a parsed peer_state dict.
    """
    if path is None:
        path = DATA_PATH

    events = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";"):
                continue

            parts = [p.strip() for p in line.split("->")]
            if len(parts) != 4:
                continue

            seq = int(parts[0])
            node_id = parts[1]
            event_type = parts[2]
            raw_detail = parts[3]

            if event_type == "EQUILIBRATE":
                # Parse peer_state=node_alpha:9;node_beta:3;...
                state_str = raw_detail.split("=", 1)[1]
                peer_state = {}
                for pair in state_str.split(";"):
                    k, v = pair.split(":")
                    peer_state[k.strip()] = int(v.strip())
                detail = peer_state
            else:
                # Parse gradient=east or similar key=value
                detail = raw_detail

            events.append({
                "seq": seq,
                "node_id": node_id,
                "event_type": event_type,
                "detail": detail,
            })

    return events


def get_all_nodes(events):
    """Extract sorted list of all unique node IDs from parsed events."""
    nodes = set()
    for e in events:
        nodes.add(e["node_id"])
    return sorted(nodes)
