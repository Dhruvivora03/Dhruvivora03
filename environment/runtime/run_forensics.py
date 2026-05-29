"""
Orchestrator for audio forensics fingerprint analysis pipeline.

Coordinates the full analysis: loading spectral data, computing fingerprints,
building the similarity matrix, clustering duplicates, and generating the report.
"""

import os
import sys
import json

# Ensure runtime directory is on path
sys.path.insert(0, os.path.dirname(__file__))

from spectrum_loader import load_spectra, get_track_ids
from fingerprint_engine import compute_track_fingerprint
from similarity_matrix import build_similarity_matrix
from cluster_builder import find_clusters, get_duplicate_groups
from forensics_report import generate_report

RUNTIME_DIR = os.path.dirname(__file__)
STATE_FILE = os.path.join(RUNTIME_DIR, "forensics_state.jsonl")
REPORT_FILE = os.path.join(RUNTIME_DIR, "dedup_report.json")


def main():
    """Run the full forensics analysis pipeline."""
    # Step 1: Load spectral data
    tracks = load_spectra()
    track_ids = get_track_ids(tracks)

    # Step 2: Compute fingerprints
    fingerprints = {}
    for tid in track_ids:
        fingerprints[tid] = compute_track_fingerprint(tracks[tid])

    # Step 3: Write state file
    write_state(track_ids, fingerprints, tracks)

    # Step 4: Generate report
    generate_report(track_ids, fingerprints, None, REPORT_FILE)

    print(f"Analysis complete. State: {STATE_FILE}, Report: {REPORT_FILE}")


def write_state(track_ids, fingerprints, tracks):
    """Write analysis state to JSONL file."""
    with open(STATE_FILE, "w") as f:
        for tid in sorted(track_ids):
            record = {
                "type": "track_fingerprint",
                "track_id": tid,
                "segment_count": fingerprints[tid]["segment_count"],
                "composite": [round(v, 4) for v in fingerprints[tid]["composite"]],
                "frame_count": len(tracks[tid]),
            }
            f.write(json.dumps(record) + "\n")

        summary = {
            "type": "analysis_summary",
            "total_tracks": len(track_ids),
            "frames_per_track": len(tracks[track_ids[0]]),
            "coefficients_per_frame": len(tracks[track_ids[0]][0]),
        }
        f.write(json.dumps(summary) + "\n")


if __name__ == "__main__":
    main()
