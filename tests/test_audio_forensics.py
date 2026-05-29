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
        """Each track must produce exactly 3 fingerprint segments.

        With 8 frames, window_size=4, and stride=2 (50% overlap):
        positions 0, 2, 4 → 3 segments.
        With stride=4 (no overlap, buggy): positions 0, 4 → only 2 segments.
        """
        report = load_report()
        for tid in EXPECTED_TRACKS:
            seg_count = report["fingerprints"][tid]["segment_count"]
            assert seg_count == 3, (
                f"{tid}: expected 3 fingerprint segments, got {seg_count}. "
                f"Sliding window must use 50% overlap (stride = window_size // 2)."
            )

    def test_composite_values_alpha(self):
        """Track alpha's composite must reflect overlapping window averages.

        With correct 50% overlap, the last coefficient captures contribution
        from overlapping middle segment. Expected value is ~1.1917.
        Non-overlapping (buggy) produces 1.2000 — detectably different.
        """
        report = load_report()
        composite = report["fingerprints"]["track_alpha"]["composite"]
        # Correct composite[5] ≈ 1.1917 (with overlap)
        # Buggy composite[5] = 1.2000 (without overlap)
        assert abs(composite[5] - 1.1917) < 0.005, (
            f"track_alpha composite[5]: expected ~1.1917, got {composite[5]:.4f}. "
            f"Indicates incorrect window stride causing coefficient drift."
        )

    def test_composite_values_delta(self):
        """Track delta's composite must match expected overlapping values."""
        report = load_report()
        composite = report["fingerprints"]["track_delta"]["composite"]
        # Correct composite[0] ≈ 3.4917
        assert abs(composite[0] - 3.4917) < 0.01, (
            f"track_delta composite[0]: expected ~3.4917, got {composite[0]:.4f}"
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
        """Exactly 2 duplicate groups must be detected.

        With correct cosine similarity and complete-linkage clustering:
        - track_alpha + track_gamma form one group (similarity > 0.99)
        - track_delta + track_zeta form another group (similarity > 0.99)
        - Remaining tracks are singletons (cross-group similarity < 0.92)
        """
        report = load_report()
        dup_count = report["clustering"]["duplicate_group_count"]
        assert dup_count == 2, (
            f"Expected 2 duplicate groups, got {dup_count}. "
            f"Check similarity normalization and linkage criterion."
        )

    def test_singleton_tracks(self):
        """Exactly 3 tracks must be singletons (not duplicates of anything).

        beta, epsilon, and eta each have unique spectral profiles that
        don't exceed the 0.92 threshold with any other track under
        complete-linkage clustering.
        """
        report = load_report()
        singletons = sorted(report["clustering"]["singleton_tracks"])
        expected = ["track_beta", "track_epsilon", "track_eta"]
        assert singletons == expected, (
            f"Expected singletons {expected}, got {singletons}"
        )


# ═══════════════════════════════════════════════════════════════
# TIER 4: Full consistency (need ALL bugs fixed)
# ═══════════════════════════════════════════════════════════════


class TestTier4Consistency:
    """Tests that validate end-to-end pipeline consistency."""

    def test_digest_fingerprint(self):
        """Report digest must match expected value for correct analysis.

        The 16-character hex digest validates that fingerprint computation,
        similarity scoring, and clustering are all correct simultaneously.
        """
        report = load_report()
        expected_digest = "312e1292f1643efd"
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
