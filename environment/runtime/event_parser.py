"""
Threat event parser for network intrusion detection.
Reads tab-separated event records from the threat log and produces
structured dictionaries for downstream analysis components.
"""

import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "threat_events.tsv")


def load_threat_events(filepath=None):
    """Load and parse the threat event log.

    Reads a TSV file with columns: seq, segment, action, payload.
    For LATERAL actions, the payload contains propagation state from
    an adjacent segment encoded as pipe-separated key:value pairs.

    Returns:
        List of event dicts with keys: seq, segment, action, payload.
        For LATERAL events, payload is a dict mapping segment->int.
        For other events, payload is the raw string.
    """
    if filepath is None:
        filepath = DATA_PATH

    events = []
    with open(filepath, "r") as fh:
        header = fh.readline()  # skip header row
        for row in fh:
            row = row.strip()
            if not row:
                continue
            cols = row.split("\t")
            if len(cols) < 4:
                continue

            seq = int(cols[0])
            segment = cols[1]
            action = cols[2]
            raw_payload = cols[3]

            if action == "LATERAL":
                # Parse propagation=seg_alpha:9|seg_beta:3|...
                state_part = raw_payload.split("=", 1)[1]
                propagation = {}
                for entry in state_part.split("|"):
                    seg_name, val = entry.split(":")
                    propagation[seg_name] = int(val)
                payload = propagation
            else:
                payload = raw_payload

            events.append({
                "seq": seq,
                "segment": segment,
                "action": action,
                "payload": payload,
            })

    return events


def extract_segments(events):
    """Get sorted list of unique segment identifiers from event stream."""
    return sorted({ev["segment"] for ev in events})
