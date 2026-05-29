"""
Hierarchical cluster builder for audio forensics pipeline.

Groups tracks into duplicate clusters using agglomerative clustering
based on similarity scores from the similarity matrix.
"""

SIMILARITY_THRESHOLD = 0.92  # minimum similarity to be considered a duplicate


def find_clusters(track_ids, similarity_matrix, threshold=SIMILARITY_THRESHOLD):
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

    return sorted(clusters, key=lambda c: (len(c), c[0]), reverse=True)


def _cluster_similarity_single(cluster_a, cluster_b, sim_matrix):
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
    return max_sim


def get_duplicate_groups(clusters):
    """Extract only multi-track clusters (actual duplicate groups).

    Returns list of clusters with 2+ tracks, indicating detected duplicates.
    """
    return [c for c in clusters if len(c) > 1]


def get_singleton_tracks(clusters):
    """Extract tracks not part of any duplicate group."""
    return sorted([c[0] for c in clusters if len(c) == 1])
