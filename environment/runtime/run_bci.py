"""
Orchestrator for EEG brainwave coherence analysis pipeline.

Coordinates the full BCI processing: decoding the electrode recording,
building spectral vectors via the accumulator, classifying coherence
relationships, and generating the final report.
"""

import os
import sys
import json

# Ensure runtime directory is on path
sys.path.insert(0, os.path.dirname(__file__))

from signal_decoder import decode_recording, get_channel_ids
from spectral_accumulator import ChannelSpectrum
from coherence_classifier import analyze_coherence
from bci_report import generate_report

RUNTIME_DIR = os.path.dirname(__file__)
STATE_FILE = os.path.join(RUNTIME_DIR, "bci_state.jsonl")
REPORT_FILE = os.path.join(RUNTIME_DIR, "coherence_report.json")


def build_spectral_vectors(events, channel_ids):
    """Process all events and build final spectral vectors."""
    accumulators = {}
    for cid in channel_ids:
        accumulators[cid] = ChannelSpectrum(cid, channel_ids)

    for event in events:
        cid = event["channel_id"]
        etype = event["signal_type"]
        details = event["details"]

        if etype == "PULSE":
            accumulators[cid].apply_pulse()
        elif etype == "SPIKE":
            accumulators[cid].apply_spike()
        elif etype == "ENTRAIN":
            accumulators[cid].apply_entrain(details["peer_state"])

    return accumulators


def write_state(accumulators, channel_ids, events):
    """Write BCI state to JSONL file."""
    with open(STATE_FILE, "w") as f:
        # Write channel states
        for cid in sorted(channel_ids):
            record = {
                "type": "channel_state",
                "channel_id": cid,
                "spectral_vector": accumulators[cid].get_vector(),
                "own_power": accumulators[cid].get_own_power(),
            }
            f.write(json.dumps(record) + "\n")

        # Write event summary
        event_counts = {}
        for e in events:
            cid = e["channel_id"]
            event_counts[cid] = event_counts.get(cid, 0) + 1

        summary = {
            "type": "event_summary",
            "total_events": len(events),
            "per_channel": event_counts,
        }
        f.write(json.dumps(summary) + "\n")


def main():
    """Run the full BCI processing pipeline."""
    # Step 1: Decode recording
    events = decode_recording()
    channel_ids = get_channel_ids(events)

    # Step 2: Build spectral vectors
    accumulators = build_spectral_vectors(events, channel_ids)

    # Step 3: Write state file
    write_state(accumulators, channel_ids, events)

    # Step 4: Extract vectors for analysis
    vectors = {}
    for cid in channel_ids:
        vectors[cid] = accumulators[cid].get_vector()

    # Step 5: Generate report
    generate_report(channel_ids, vectors, events, REPORT_FILE)

    print(f"BCI analysis complete. State: {STATE_FILE}, Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
