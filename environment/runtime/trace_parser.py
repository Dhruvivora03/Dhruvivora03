"""
Trace parser for particle collision chamber log files.

Reads the arrow-separated event trace and produces structured event records
for downstream processing by the momentum tracker and analyzer.
"""

import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "collision_trace.log")


def parse_trace(filepath=None):
    """Parse collision trace log into structured event list.

    Returns a list of dicts with keys:
        seq, particle_id, event_type, details (dict)
    """
    if filepath is None:
        filepath = DATA_PATH

    events = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            parts = [p.strip() for p in line.split("->")]
            if len(parts) != 4:
                continue

            seq = int(parts[0])
            particle_id = parts[1]
            event_type = parts[2]
            raw_details = parts[3]

            details = {}
            if event_type == "COLLIDE":
                # Parse peer_state=particle_alpha:7;particle_beta:6;...
                prefix = "peer_state="
                if raw_details.startswith(prefix):
                    state_str = raw_details[len(prefix):]
                    peer_state = {}
                    for pair in state_str.split(";"):
                        entity, val = pair.split(":")
                        peer_state[entity.strip()] = int(val.strip())
                    details["peer_state"] = peer_state
            else:
                # Parse delta=N
                for kv in raw_details.split(","):
                    k, v = kv.split("=")
                    details[k.strip()] = int(v.strip())

            events.append({
                "seq": seq,
                "particle_id": particle_id,
                "event_type": event_type,
                "details": details,
            })

    return events


def get_particle_ids(events):
    """Extract sorted unique particle IDs from event list."""
    ids = set()
    for e in events:
        ids.add(e["particle_id"])
    return sorted(ids)
