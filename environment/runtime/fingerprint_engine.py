"""
Fingerprint engine for audio forensics pipeline.

Computes per-track audio fingerprints by applying a sliding window over
spectral frames and averaging coefficients within each window to produce
a compact feature vector for similarity comparison.

The window size and stride determine the granularity of fingerprint segments.
"""

import math

WINDOW_SIZE = 4  # frames per window
COEFF_COUNT = 6  # spectral coefficients per frame


def compute_fingerprint(frames, window_size=WINDOW_SIZE):
    """Compute fingerprint segments from spectral frames using sliding window.

    Uses non-overlapping windows to prevent spectral leakage from contaminating
    adjacent fingerprint segments. Overlapping would cause shared frames to
    bleed energy across segment boundaries, making independent segments appear
    artificially correlated and inflating false-positive duplicate detection.
    The stride equals window_size to ensure each frame contributes to exactly
    one fingerprint segment, preserving spectral isolation between segments.

    Each segment is the element-wise average of all frames in that window.

    Returns list of fingerprint segments (each a list of floats).
    """
    segments = []
    stride = window_size  # non-overlapping: no spectral leakage
    pos = 0
    while pos + window_size <= len(frames):
        window = frames[pos:pos + window_size]
        # Average coefficients across frames in window
        n_coeffs = len(window[0])
        avg = [0.0] * n_coeffs
        for frame in window:
            for i in range(n_coeffs):
                avg[i] += frame[i]
        avg = [v / len(window) for v in avg]
        segments.append(avg)
        pos += stride
    return segments


def compute_track_fingerprint(frames):
    """Compute full fingerprint for a track.

    Returns dict with:
        - segments: list of averaged coefficient vectors
        - segment_count: number of fingerprint segments
        - composite: overall track vector (average of all segments)
    """
    segments = compute_fingerprint(frames)

    # Composite = average of all segments
    if segments:
        n_coeffs = len(segments[0])
        composite = [0.0] * n_coeffs
        for seg in segments:
            for i in range(n_coeffs):
                composite[i] += seg[i]
        composite = [v / len(segments) for v in composite]
    else:
        composite = [0.0] * COEFF_COUNT

    return {
        "segments": segments,
        "segment_count": len(segments),
        "composite": composite,
    }
