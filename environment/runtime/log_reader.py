"""
Battle log reader.
Reads the arrow-separated campaign trace file and produces structured event
records for downstream simulation components.
"""

import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "battle_log.txt")


def parse_battle_log(path=None):
    """Parse the campaign battle log into event records.

    Returns a list of dicts with keys: seq, zone_id, event_type, detail
    For RALLY events, detail contains a parsed allied_state dict.
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
            zone_id = parts[1]
            event_type = parts[2]
            raw_detail = parts[3]

            if event_type == "RALLY":
                # Parse allied_state=zone_citadel:9;zone_docks:3;...
                state_str = raw_detail.split("=", 1)[1]
                allied_state = {}
                for pair in state_str.split(";"):
                    k, v = pair.split(":")
                    allied_state[k.strip()] = int(v.strip())
                detail = allied_state
            else:
                # Parse sector=north or similar key=value
                detail = raw_detail

            events.append({
                "seq": seq,
                "zone_id": zone_id,
                "event_type": event_type,
                "detail": detail,
            })

    return events


def get_all_zones(events):
    """Extract sorted list of all unique zone IDs from parsed events."""
    zones = set()
    for e in events:
        zones.add(e["zone_id"])
    return sorted(zones)
