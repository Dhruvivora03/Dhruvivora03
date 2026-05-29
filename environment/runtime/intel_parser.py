"""
Threat intelligence event parser.

Reads the pipe-separated intrusion event log and produces structured
event records for downstream correlation analysis. Each record captures
the sequence number, originating network segment, event classification,
and parsed payload appropriate to the event type.

This module implements the STIX-lite ingestion format used by the SOC
correlation engine. Events are categorized into three classes:
  - PROBE: Reconnaissance or low-impact scanning (severity weight 1)
  - BREACH: Active exploitation or compromise (severity weight 2)
  - CORRELATE: Cross-segment intelligence synchronization

The parser validates field counts and silently drops malformed records
to maintain pipeline robustness during high-volume ingestion.
"""

import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "intrusion_events.log")

# Event severity weights per NIST SP 800-61 classification
SEVERITY_WEIGHTS = {
    "PROBE": 1,
    "BREACH": 2,
    "CORRELATE": 0,  # Intelligence sharing has no direct severity
}


def parse_events(path=None):
    """Parse the intrusion event log into structured records.

    Returns a list of dicts with keys: seq, segment_id, event_class, payload.
    For CORRELATE events, payload contains a parsed dict of segment threat levels.
    For PROBE/BREACH events, payload contains the attack vector identifier.

    Records are validated for field completeness; malformed lines are
    silently discarded to maintain pipeline continuity.
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
                # Parse intel_state=dmz:9;vault:8;...
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
    """Extract unique segment identifiers in discovery order.

    Preserves first-seen ordering which corresponds to the chronological
    order segments first appeared in the threat feed. This ordering is
    used downstream for deterministic vector construction.
    """
    seen = set()
    ids = []
    for e in events:
        sid = e["segment_id"]
        if sid not in seen:
            seen.add(sid)
            ids.append(sid)
    return ids


def compute_event_density(events, segments):
    """Compute per-segment event density metrics.

    Returns a dict mapping segment_id to total weighted event count,
    useful for downstream normalization of threat vectors.
    """
    density = {s: 0 for s in segments}
    for e in events:
        weight = SEVERITY_WEIGHTS.get(e["event_class"], 0)
        density[e["segment_id"]] += weight
    return density
