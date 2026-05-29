"""
Spectrum loader for audio forensics pipeline.

Reads the spectral coefficient dump and produces per-track frame arrays
for downstream processing by the fingerprint engine and similarity analyzer.
"""

import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "spectral_coefficients.dat")


def load_spectra(filepath=None):
    """Load spectral coefficients from data file.

    Returns dict mapping track_id -> list of frames,
    where each frame is a list of float coefficients.
    """
    if filepath is None:
        filepath = DATA_PATH

    tracks = {}
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 3:
                continue

            track_id = parts[0]
            frame_idx = int(parts[1])
            coefficients = [float(x) for x in parts[2].split(",")]

            if track_id not in tracks:
                tracks[track_id] = []
            tracks[track_id].append(coefficients)

    return tracks


def get_track_ids(tracks):
    """Return sorted list of track IDs."""
    return sorted(tracks.keys())
