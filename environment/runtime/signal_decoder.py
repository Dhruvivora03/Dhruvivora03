"""
Signal decoder for EEG brainwave coherence analysis.

Reads the arrow-separated electrode recording and produces structured
signal events for downstream processing by the spectral accumulator
and coherence classifier.
"""

import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "eeg_recording.dat")


def decode_recording(filepath=None):
    """Decode EEG recording into structured event list.

    Returns a list of dicts with keys:
        seq, channel_id, signal_type, details (dict)
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
            channel_id = parts[1]
            signal_type = parts[2]
            raw_details = parts[3]

            details = {}
            if signal_type == "ENTRAIN":
                # Parse peer_state=electrode_fp1:7;electrode_fp2:6;...
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
                "channel_id": channel_id,
                "signal_type": signal_type,
                "details": details,
            })

    return events


def get_channel_ids(events):
    """Extract sorted unique channel IDs from event list."""
    ids = set()
    for e in events:
        ids.add(e["channel_id"])
    return sorted(ids)
