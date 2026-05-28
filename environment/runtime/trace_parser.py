"""
Trace parser for particle field simulation logs.

Reads the arrow-separated event log and produces structured event records.
Each record contains the sequence number, particle identifier, event type,
and parsed detail fields appropriate to the event category.
"""

import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "particle_field.log")


def parse_trace(path=None):
    """Parse the particle field trace log into structured event records.

    Returns a list of dicts with keys: seq, particle_id, event_type, detail.
    For COUPLE events, detail contains a parsed dict of peer energy states.
    For DRIFT events, detail contains the displacement float.
    For COLLIDE events, detail contains the collision partner string.
    """
    if path is None:
        path = DATA_PATH

    events = []
    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            parts = [p.strip() for p in line.split("->")]
            if len(parts) != 4:
                continue

            seq = int(parts[0])
            particle_id = parts[1]
            event_type = parts[2]
            raw_detail = parts[3]

            if event_type == "COUPLE":
                # Parse peer_state=alpha:7;beta:3;...
                state_str = raw_detail.split("=", 1)[1]
                peer_state = {}
                for pair in state_str.split(";"):
                    k, v = pair.split(":")
                    peer_state[k] = int(v)
                detail = peer_state
            elif event_type == "DRIFT":
                detail = float(raw_detail.split("=", 1)[1])
            elif event_type == "COLLIDE":
                detail = raw_detail.split("=", 1)[1]
            else:
                detail = raw_detail

            events.append({
                "seq": seq,
                "particle_id": particle_id,
                "event_type": event_type,
                "detail": detail,
            })

    return events


def get_particle_ids(events):
    """Extract unique particle identifiers in discovery order."""
    seen = set()
    ids = []
    for e in events:
        pid = e["particle_id"]
        if pid not in seen:
            seen.add(pid)
            ids.append(pid)
    return ids
