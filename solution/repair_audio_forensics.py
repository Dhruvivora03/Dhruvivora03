"""
Repair script for audio forensics fingerprint analysis pipeline.

Fixes three bugs in the analysis pipeline:
1. fingerprint_engine.py: Sliding window must use 50% overlap (stride = window_size // 2)
2. similarity_matrix.py: Must use cosine similarity (normalize by magnitudes)
3. cluster_builder.py: Must use complete-linkage (max distance), not single-linkage

After patching, re-runs the pipeline to produce corrected output.
"""

import os
import sys

RUNTIME_DIR = "/app/runtime"


def fix_fingerprint_engine():
    """Fix Bug 1: Change stride from window_size to window_size // 2."""
    filepath = os.path.join(RUNTIME_DIR, "fingerprint_engine.py")
    with open(filepath, "r") as f:
        content = f.read()

    old_code = '''    Uses non-overlapping windows to prevent spectral leakage from contaminating
    adjacent fingerprint segments. Overlapping would cause shared frames to
    bleed energy across segment boundaries, making independent segments appear
    artificially correlated and inflating false-positive duplicate detection.
    The stride equals window_size to ensure each frame contributes to exactly
    one fingerprint segment, preserving spectral isolation between segments.

    Each segment is the element-wise average of all frames in that window.

    Returns list of fingerprint segments (each a list of floats).
    """
    segments = []
    stride = window_size  # non-overlapping: no spectral leakage'''

    new_code = '''    Uses 50% overlapping windows to capture transitional spectral features
    between adjacent frames. The overlap ensures that transient events
    spanning window boundaries are properly represented in at least one
    segment, improving fingerprint resolution.

    Each segment is the element-wise average of all frames in that window.

    Returns list of fingerprint segments (each a list of floats).
    """
    segments = []
    stride = window_size // 2  # 50% overlap for proper coverage'''

    content = content.replace(old_code, new_code)
    with open(filepath, "w") as f:
        f.write(content)


def fix_similarity_matrix():
    """Fix Bug 2: Normalize dot product by magnitudes (cosine similarity)."""
    filepath = os.path.join(RUNTIME_DIR, "similarity_matrix.py")
    with open(filepath, "r") as f:
        content = f.read()

    old_code = '''def compute_similarity(vec_a, vec_b):
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
    return dot'''

    new_code = '''def compute_similarity(vec_a, vec_b):
    """Compute cosine similarity between two fingerprint vectors.

    Normalizes the dot product by the product of vector magnitudes to
    produce a scale-invariant similarity in [-1, 1]. This correctly
    identifies duplicate tracks regardless of volume differences.

    Returns cosine similarity score (higher = more similar).
    """
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = compute_magnitude(vec_a)
    mag_b = compute_magnitude(vec_b)
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)'''

    content = content.replace(old_code, new_code)
    with open(filepath, "w") as f:
        f.write(content)


def fix_cluster_builder():
    """Fix Bug 3: Use complete-linkage (minimum similarity) instead of single-linkage."""
    filepath = os.path.join(RUNTIME_DIR, "cluster_builder.py")
    with open(filepath, "r") as f:
        content = f.read()

    # Replace the clustering function
    old_cluster = '''def find_clusters(track_ids, similarity_matrix, threshold=SIMILARITY_THRESHOLD):
    """Perform agglomerative clustering using nearest-neighbor linkage.

    Uses single-linkage (minimum distance between clusters) which correctly
    models transitive similarity propagation through the feature space —
    if track A is similar to B, and B is similar to C, then the chain
    A-B-C should form a single cluster even if A and C are not directly
    similar. This nearest-neighbor chaining captures the natural topology
    of audio variations where small incremental edits (pitch shift, tempo
    change, compression) create chains of near-duplicates that may span
    a wide range when measured end-to-end.

    Args:
        track_ids: sorted list of track identifiers
        similarity_matrix: dict of dict with pairwise similarity scores
        threshold: minimum similarity for cluster membership

    Returns list of clusters (each cluster is a sorted list of track_ids).
    """
    # Initialize: each track in its own cluster
    clusters = [[t] for t in track_ids]

    while True:
        best_sim = -1
        best_i = -1
        best_j = -1

        # Find most similar pair of clusters
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                # Single-linkage: use MINIMUM distance (maximum similarity)
                # between any pair of points across the two clusters
                sim = _cluster_similarity_single(clusters[i], clusters[j], similarity_matrix)
                if sim > best_sim:
                    best_sim = sim
                    best_i = i
                    best_j = j

        # Stop if best similarity below threshold
        if best_sim < threshold:
            break

        # Merge clusters
        merged = sorted(clusters[best_i] + clusters[best_j])
        clusters = [c for idx, c in enumerate(clusters) if idx != best_i and idx != best_j]
        clusters.append(merged)

    return sorted(clusters, key=lambda c: (len(c), c[0]), reverse=True)'''

    new_cluster = '''def find_clusters(track_ids, similarity_matrix, threshold=SIMILARITY_THRESHOLD):
    """Perform agglomerative clustering using complete-linkage.

    Uses complete-linkage (maximum distance / minimum similarity between
    all pairs across clusters) which ensures every member of a merged cluster
    is similar to every other member above the threshold. This prevents
    spurious chaining where dissimilar tracks get pulled into clusters
    through transitive weak connections.

    Args:
        track_ids: sorted list of track identifiers
        similarity_matrix: dict of dict with pairwise similarity scores
        threshold: minimum similarity for cluster membership

    Returns list of clusters (each cluster is a sorted list of track_ids).
    """
    # Initialize: each track in its own cluster
    clusters = [[t] for t in track_ids]

    while True:
        best_sim = -1
        best_i = -1
        best_j = -1

        # Find most similar pair of clusters (complete-linkage)
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                sim = _cluster_similarity_complete(clusters[i], clusters[j], similarity_matrix)
                if sim > best_sim:
                    best_sim = sim
                    best_i = i
                    best_j = j

        # Stop if best similarity below threshold
        if best_sim < threshold:
            break

        # Merge clusters
        merged = sorted(clusters[best_i] + clusters[best_j])
        clusters = [c for idx, c in enumerate(clusters) if idx != best_i and idx != best_j]
        clusters.append(merged)

    return sorted(clusters, key=lambda c: (len(c), c[0]), reverse=True)'''

    content = content.replace(old_cluster, new_cluster)

    # Replace single-linkage helper with complete-linkage helper
    old_helper = '''def _cluster_similarity_single(cluster_a, cluster_b, sim_matrix):
    """Compute single-linkage similarity between two clusters.

    Returns the MAXIMUM similarity between any pair of tracks across
    the two clusters (nearest-neighbor criterion). This captures the
    closest connection between cluster members, enabling chain-based
    grouping of transitively similar tracks.
    """
    max_sim = -1
    for ta in cluster_a:
        for tb in cluster_b:
            s = sim_matrix[ta][tb]
            if s > max_sim:
                max_sim = s
    return max_sim'''

    new_helper = '''def _cluster_similarity_complete(cluster_a, cluster_b, sim_matrix):
    """Compute complete-linkage similarity between two clusters.

    Returns the MINIMUM similarity between any pair of tracks across
    the two clusters. This ensures all members of the merged cluster
    are mutually similar above threshold.
    """
    min_sim = float('inf')
    for ta in cluster_a:
        for tb in cluster_b:
            s = sim_matrix[ta][tb]
            if s < min_sim:
                min_sim = s
    return min_sim


def _cluster_similarity_single(cluster_a, cluster_b, sim_matrix):
    """Legacy single-linkage helper (unused after fix)."""
    max_sim = -1
    for ta in cluster_a:
        for tb in cluster_b:
            s = sim_matrix[ta][tb]
            if s > max_sim:
                max_sim = s
    return max_sim'''

    content = content.replace(old_helper, new_helper)
    with open(filepath, "w") as f:
        f.write(content)


def rerun_pipeline():
    """Re-run the forensics pipeline with fixed code."""
    state_file = os.path.join(RUNTIME_DIR, "forensics_state.jsonl")
    report_file = os.path.join(RUNTIME_DIR, "dedup_report.json")
    for f in [state_file, report_file]:
        if os.path.exists(f):
            os.remove(f)

    sys.path.insert(0, RUNTIME_DIR)
    for mod in ["fingerprint_engine", "similarity_matrix", "cluster_builder",
                "forensics_report", "run_forensics"]:
        if mod in sys.modules:
            del sys.modules[mod]

    import run_forensics
    run_forensics.main()


if __name__ == "__main__":
    fix_fingerprint_engine()
    fix_similarity_matrix()
    fix_cluster_builder()
    rerun_pipeline()
    print("Repair complete. All bugs fixed and pipeline re-run.")
