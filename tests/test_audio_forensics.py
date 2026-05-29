"""
Test suite for audio forensics fingerprint analysis pipeline.

Validates analysis correctness across four tiers:
  Tier 1 (6 tests): Structural validation — output existence and format
  Tier 2 (3 tests): Fingerprint computation — segment count and composites
  Tier 3 (3 tests): Similarity and clustering — correct scores and groups
  Tier 4 (2 tests): Full consistency — digest and cross-validation
"""

import json
import os
import sys
import math
import hashlib

sys.path.insert(0, "/app/runtime")

STATE_FILE = "/app/runtime/forensics_state.jsonl"
REPORT_FILE = "/app/runtime/dedup_report.json"

EXPECTED_TRACKS = [
    "track_alpha",
    "track_beta",
    "track_delta",
    "track_epsilon",
    "track_eta",
    "track_gamma",
    "track_zeta",
]

WINDOW_SIZE = 4
SIMILARITY_THRESHOLD = 0.92


def load_state():
    """Load forensics state from JSONL file."""
    records = []
    with open(STATE_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_report():
    """Load deduplication report from JSON file."""
    with open(REPORT_FILE, "r") as f:
        return json.load(f)


def load_raw_spectra():
    """Load raw spectral data directly from source file for reference computation."""
    from spectrum_loader import load_spectra
    return load_spectra()


def reference_fingerprint(frames):
    """Compute correct fingerprint with 50% overlap sliding window."""
    segments = []
    stride = WINDOW_SIZE // 2
    pos = 0
    while pos + WINDOW_SIZE <= len(frames):
        window = frames[pos:pos + WINDOW_SIZE]
        n_coeffs = len(window[0])
        avg = [0.0] * n_coeffs
        for frame in window:
            for i in range(n_coeffs):
                avg[i] += frame[i]
        avg = [v / len(window) for v in avg]
        segments.append(avg)
        pos += stride
    # Composite
    n_coeffs = len(segments[0])
    composite = [0.0] * n_coeffs
    for seg in segments:
        for i in range(n_coeffs):
            composite[i] += seg[i]
    composite = [v / len(segments) for v in composite]
    return {"segments": segments, "segment_count": len(segments), "composite": composite}


def reference_cosine_similarity(vec_a, vec_b):
    """Compute correct cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(x * x for x in vec_a))
    mag_b = math.sqrt(sum(x * x for x in vec_b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def reference_complete_linkage_clusters(track_ids, sim_matrix, threshold):
    """Compute correct clusters using complete-linkage."""
    clusters = [[t] for t in track_ids]
    while True:
        best_sim = -1
        best_i = -1
        best_j = -1
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                # Complete-linkage: minimum similarity across all pairs
                min_sim = float("inf")
                for ta in clusters[i]:
                    for tb in clusters[j]:
                        s = sim_matrix[ta][tb]
                        if s < min_sim:
                            min_sim = s
                if min_sim > best_sim:
                    best_sim = min_sim
                    best_i = i
                    best_j = j
        if best_sim < threshold:
            break
        merged = sorted(clusters[best_i] + clusters[best_j])
        clusters = [c for idx, c in enumerate(clusters) if idx != best_i and idx != best_j]
        clusters.append(merged)
    return sorted(clusters, key=lambda c: (len(c), c[0]), reverse=True)


def compute_reference_results():
    """Compute full reference results from raw source data."""
    tracks = load_raw_spectra()
    track_ids = sorted(tracks.keys())

    # Correct fingerprints
    fingerprints = {}
    for tid in track_ids:
        fingerprints[tid] = reference_fingerprint(tracks[tid])

    composites = {t: fingerprints[t]["composite"] for t in track_ids}

    # Correct similarity matrix
    sim_matrix = {}
    pairs = []
    for t1 in track_ids:
        sim_matrix[t1] = {}
        for t2 in track_ids:
            score = reference_cosine_similarity(composites[t1], composites[t2])
            sim_matrix[t1][t2] = round(score, 6)
            if t1 < t2:
                pairs.append((t1, t2, round(score, 6)))
    pairs.sort(key=lambda x: x[2], reverse=True)

    # Correct clusters
    clusters = reference_complete_linkage_clusters(track_ids, sim_matrix, SIMILARITY_THRESHOLD)
    dup_groups = [c for c in clusters if len(c) > 1]
    singletons = sorted([c[0] for c in clusters if len(c) == 1])

    # Correct digest
    h = hashlib.sha256()
    for t in sorted(track_ids):
        vec_str = ",".join(f"{v:.4f}" for v in composites[t])
        h.update(f"{t}:{vec_str}\n".encode())
    for cluster in sorted(clusters, key=lambda c: c[0]):
        h.update(f"cluster:{','.join(cluster)}\n".encode())
    for t1, t2, score in pairs[:5]:
        h.update(f"pair:{t1},{t2},{score:.6f}\n".encode())
    digest = h.hexdigest()[:16]

    return {
        "fingerprints": fingerprints,
        "composites": composites,
        "sim_matrix": sim_matrix,
        "pairs": pairs,
        "clusters": clusters,
        "dup_groups": dup_groups,
        "singletons": singletons,
        "digest": digest,
    }


# ═══════════════════════════════════════════════════════════════
# TIER 1: Structural validation (always pass with buggy code)
# ═══════════════════════════════════════════════════════════════


class TestTier1Structural:
    """Structural tests that validate output format and existence."""

    def test_output_files_exist(self):
        """Both state and report files must be generated."""
        assert os.path.isfile(STATE_FILE), f"State file missing: {STATE_FILE}"
        assert os.path.isfile(REPORT_FILE), f"Report file missing: {REPORT_FILE}"

    def test_track_count(self):
        """Analysis must process exactly 7 audio tracks."""
        report = load_report()
        assert report["analysis_summary"]["track_count"] == 7

    def test_track_ids(self):
        """All expected track IDs must be present in report."""
        report = load_report()
        tracks = sorted(report["analysis_summary"]["tracks"])
        assert tracks == EXPECTED_TRACKS

    def test_composite_dimensions(self):
        """Each composite fingerprint must have 6 coefficients."""
        report = load_report()
        for tid in EXPECTED_TRACKS:
            composite = report["fingerprints"][tid]["composite"]
            assert len(composite) == 6, (
                f"{tid}: composite has {len(composite)} coefficients, expected 6"
            )

    def test_similarity_pairs_present(self):
        """Similarity section must contain ranked pairs."""
        report = load_report()
        assert "top_pairs" in report["similarity"]
        assert len(report["similarity"]["top_pairs"]) > 0

    def test_clustering_structure(self):
        """Clustering section must have required fields."""
        report = load_report()
        cl = report["clustering"]
        assert "clusters" in cl
        assert "duplicate_groups" in cl
        assert "duplicate_group_count" in cl
        assert "singleton_tracks" in cl
        # All tracks must appear in exactly one cluster
        all_tracks_in_clusters = []
        for cluster in cl["clusters"]:
            all_tracks_in_clusters.extend(cluster)
        assert sorted(all_tracks_in_clusters) == EXPECTED_TRACKS


# ═══════════════════════════════════════════════════════════════
# TIER 2: Fingerprint computation (need Bug 1 fixed)
# ═══════════════════════════════════════════════════════════════


class TestTier2Fingerprints:
    """Tests that validate fingerprint segment computation."""

    def test_segment_count(self):
        """Each track must produce the correct number of fingerprint segments.

        With 8 frames, window_size=4, and stride=2 (50% overlap):
        positions 0, 2, 4 → 3 segments.
        """
        ref = compute_reference_results()
        report = load_report()
        for tid in EXPECTED_TRACKS:
            expected_count = ref["fingerprints"][tid]["segment_count"]
            actual_count = report["fingerprints"][tid]["segment_count"]
            assert actual_count == expected_count, (
                f"{tid}: expected {expected_count} fingerprint segments, got {actual_count}. "
                f"Sliding window must use 50% overlap (stride = window_size // 2)."
            )

    def test_composite_values_alpha(self):
        """Track alpha's composite must reflect overlapping window averages.

        With correct 50% overlap, the composite captures contribution from
        overlapping middle segment. Non-overlapping produces different values.
        """
        ref = compute_reference_results()
        report = load_report()
        expected_val = ref["composites"]["track_alpha"][5]
        actual_val = report["fingerprints"]["track_alpha"]["composite"][5]
        assert abs(actual_val - expected_val) < 0.005, (
            f"track_alpha composite[5]: expected ~{expected_val:.4f}, got {actual_val:.4f}. "
            f"Indicates incorrect window stride causing coefficient drift."
        )

    def test_composite_values_delta(self):
        """Track delta's first coefficient must be within valid spectral range.

        The composite first coefficient for track_delta must lie between 3.0
        and 4.0 given the input data range. This validates basic averaging
        correctness independent of overlap strategy.
        """
        report = load_report()
        actual_val = report["fingerprints"]["track_delta"]["composite"][0]
        assert 3.0 <= actual_val <= 4.0, (
            f"track_delta composite[0]: expected in [3.0, 4.0], got {actual_val:.4f}. "
            f"Composite averaging is fundamentally broken."
        )


# ═══════════════════════════════════════════════════════════════
# TIER 3: Similarity and clustering (need Bugs 2+3 fixed)
# ═══════════════════════════════════════════════════════════════


class TestTier3SimilarityClustering:
    """Tests that validate similarity computation and cluster formation."""

    def test_similarity_normalized(self):
        """Top similarity score must be in [0, 1] range (cosine similarity).

        Correct cosine similarity divides by magnitude product, yielding
        values in [-1, 1]. Raw dot product would give values >> 1.
        """
        report = load_report()
        top_pairs = report["similarity"]["top_pairs"]
        top_score = top_pairs[0][2]
        assert 0.0 <= top_score <= 1.0, (
            f"Top similarity score is {top_score}, which is outside [0,1]. "
            f"Similarity must use cosine (normalized dot product), not raw inner product."
        )

    def test_duplicate_group_count(self):
        """Correct number of duplicate groups must be detected.

        With correct cosine similarity and complete-linkage clustering,
        only tracks with pairwise similarity > threshold in all directions
        form duplicate groups.
        """
        ref = compute_reference_results()
        report = load_report()
        expected_count = len(ref["dup_groups"])
        actual_count = report["clustering"]["duplicate_group_count"]
        assert actual_count == expected_count, (
            f"Expected {expected_count} duplicate groups, got {actual_count}. "
            f"Check similarity normalization and linkage criterion."
        )

    def test_singleton_tracks(self):
        """Correct set of tracks must be classified as singletons.

        Tracks with unique spectral profiles that don't exceed the similarity
        threshold with any other track under complete-linkage clustering.
        """
        ref = compute_reference_results()
        report = load_report()
        expected_singletons = ref["singletons"]
        actual_singletons = sorted(report["clustering"]["singleton_tracks"])
        assert actual_singletons == expected_singletons, (
            f"Expected singletons {expected_singletons}, got {actual_singletons}"
        )


# ═══════════════════════════════════════════════════════════════
# TIER 4: Full consistency (need ALL bugs fixed)
# ═══════════════════════════════════════════════════════════════


class TestTier4Consistency:
    """Tests that validate end-to-end pipeline consistency."""

    def test_digest_fingerprint(self):
        """Report digest must match the reference digest computed from source data.

        The 16-character hex digest validates that fingerprint computation,
        similarity scoring, and clustering are all correct simultaneously.
        """
        ref = compute_reference_results()
        report = load_report()
        expected_digest = ref["digest"]
        actual_digest = report["validation"]["digest"]
        assert actual_digest == expected_digest, (
            f"Digest mismatch: expected {expected_digest}, got {actual_digest}. "
            f"This indicates one or more pipeline stages produce incorrect results."
        )

    def test_state_report_cross_validation(self):
        """State file composites must match report fingerprint composites."""
        state = load_state()
        report = load_report()

        state_composites = {}
        for record in state:
            if record["type"] == "track_fingerprint":
                state_composites[record["track_id"]] = record["composite"]

        for tid in EXPECTED_TRACKS:
            assert tid in state_composites, f"{tid} missing from state file"
            assert tid in report["fingerprints"], f"{tid} missing from report"
            state_comp = state_composites[tid]
            report_comp = report["fingerprints"][tid]["composite"]
            for i, (sv, rv) in enumerate(zip(state_comp, report_comp)):
                assert abs(sv - rv) < 0.0001, (
                    f"{tid} composite[{i}] mismatch: state={sv}, report={rv}"
                )
