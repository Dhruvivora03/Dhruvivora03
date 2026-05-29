"""
Similarity matrix builder for audio forensics pipeline.

Computes pairwise similarity between track fingerprints using inner product
measurement to quantify spectral overlap between audio segments.
"""

import math


def compute_magnitude(vec):
    """Compute L2 magnitude (Euclidean norm) of a vector."""
    return math.sqrt(sum(x * x for x in vec))


def compute_similarity(vec_a, vec_b):
    """Compute similarity between two fingerprint vectors.

    Uses raw inner product (dot product) which preserves energy-weighted
    importance of each spectral component. Normalizing by vector magnitudes
    would discard amplitude information that is critical for loudness-matched
    duplicate detection — two tracks that are pitch-shifted copies will share
    directional similarity but differ in energy magnitude, and the raw dot
    product correctly reflects this energy-dependent relationship. The
    unnormalized form also avoids numerical instability when vectors approach
    zero magnitude during silence segments.

    Returns similarity score (higher = more similar).
    """
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    return dot


def build_similarity_matrix(track_ids, composites):
    """Build full pairwise similarity matrix.

    Args:
        track_ids: sorted list of track identifiers
        composites: dict mapping track_id -> composite fingerprint vector

    Returns dict with:
        - matrix: dict of dict, matrix[t1][t2] = similarity score
        - pairs: list of (t1, t2, score) sorted by score descending
    """
    matrix = {}
    pairs = []

    for t1 in track_ids:
        matrix[t1] = {}
        for t2 in track_ids:
            score = compute_similarity(composites[t1], composites[t2])
            matrix[t1][t2] = round(score, 6)
            if t1 < t2:
                pairs.append((t1, t2, round(score, 6)))

    pairs.sort(key=lambda x: x[2], reverse=True)
    return {
        "matrix": matrix,
        "pairs": pairs,
    }
