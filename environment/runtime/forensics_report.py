"""
Forensics report writer for audio fingerprint analysis.

Generates the final deduplication report in JSON format, including
per-track fingerprints, similarity scores, cluster assignments, and
a consistency digest for validation of the full analysis pipeline.
"""

import json
import hashlib
from similarity_matrix import compute_similarity, build_similarity_matrix
from cluster_builder import find_clusters, get_duplicate_groups, get_singleton_tracks


def compute_digest(track_ids, composites, clusters, top_pairs):
    """Compute 16-char hex digest of forensics results for validation.

    Combines composite fingerprints, cluster assignments, and top similarity
    pairs into a single fingerprint that validates end-to-end correctness.
    """
    h = hashlib.sha256()

    # Include composite vectors
    for t in sorted(track_ids):
        vec_str = ",".join(f"{v:.4f}" for v in composites[t])
        h.update(f"{t}:{vec_str}\n".encode())

    # Include cluster assignments
    for cluster in sorted(clusters, key=lambda c: c[0]):
        h.update(f"cluster:{','.join(cluster)}\n".encode())

    # Include top 5 pairs
    for t1, t2, score in top_pairs[:5]:
        h.update(f"pair:{t1},{t2},{score:.6f}\n".encode())

    return h.hexdigest()[:16]


def generate_report(track_ids, fingerprints, events_unused, output_path):
    """Generate full forensics report as JSON.

    Computes similarity matrix, performs clustering, and writes report.
    """
    # Extract composites
    composites = {t: fingerprints[t]["composite"] for t in track_ids}

    # Build similarity matrix
    sim_data = build_similarity_matrix(track_ids, composites)

    # Perform clustering
    clusters = find_clusters(track_ids, sim_data["matrix"])
    dup_groups = get_duplicate_groups(clusters)
    singletons = get_singleton_tracks(clusters)

    # Compute digest
    digest = compute_digest(track_ids, composites, clusters, sim_data["pairs"])

    # Build report
    report = {
        "analysis_summary": {
            "track_count": len(track_ids),
            "tracks": sorted(track_ids),
        },
        "fingerprints": {},
        "similarity": {
            "top_pairs": [[t1, t2, score] for t1, t2, score in sim_data["pairs"][:10]],
            "threshold": 0.92,
        },
        "clustering": {
            "clusters": [sorted(c) for c in clusters],
            "duplicate_groups": [sorted(g) for g in dup_groups],
            "duplicate_group_count": len(dup_groups),
            "singleton_tracks": singletons,
        },
        "validation": {
            "digest": digest,
        },
    }

    # Add per-track fingerprint info
    for t in sorted(track_ids):
        report["fingerprints"][t] = {
            "segment_count": fingerprints[t]["segment_count"],
            "composite": [round(v, 4) for v in fingerprints[t]["composite"]],
        }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    return report
