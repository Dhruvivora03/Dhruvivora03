"""
Threat intelligence event parser for the SOC correlation engine.

Reads the pipe-separated intrusion event log and produces structured
event records for downstream threat analysis. Supports three event classes:
PROBE (severity +1), BREACH (severity +2), and CORRELATE (intel sync).
"""

import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "intrusion_events.log")


def parse_events(path=None):
    """Parse the intrusion event log into structured records.

    Returns a list of dicts with keys: seq, segment_id, event_class, payload.
    CORRELATE payloads are parsed into dicts; PROBE/BREACH into strings.
    """
    if path is None:
        path = DATA_PATH

    events = []
    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 4:
                continue

            seq = int(parts[0])
            segment_id = parts[1]
            event_class = parts[2]
            raw_payload = parts[3]

            if event_class == "CORRELATE":
                state_str = raw_payload.split("=", 1)[1]
                intel_state = {}
                for pair in state_str.split(";"):
                    k, v = pair.split(":")
                    intel_state[k] = int(v)
                payload = intel_state
            elif event_class in ("PROBE", "BREACH"):
                payload = raw_payload.split("=", 1)[1]
            else:
                payload = raw_payload

            events.append({
                "seq": seq,
                "segment_id": segment_id,
                "event_class": event_class,
                "payload": payload,
            })

    return events


def get_segment_ids(events):
    """Extract unique segment identifiers in first-seen order."""
    seen = set()
    ids = []
    for e in events:
        sid = e["segment_id"]
        if sid not in seen:
            seen.add(sid)
            ids.append(sid)
    return ids
