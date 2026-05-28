"""
Tests for the network intrusion detection pipeline.
Validates structural output, threat state correctness, segment isolation
classification, and full detection consistency.
"""

import json
import os
import sys
import hashlib
import base64

sys.path.insert(0, "/app/runtime")

FINDINGS_FILE = "/app/runtime/detection_findings.jsonl"
SUMMARY_FILE = "/app/runtime/detection_summary.json"

# Verification oracle: base64-encoded expected values from a verified
# correct detection run. Decode at runtime for comparison.
_ORACLE_B64 = (
    "eyJmaW5nZXJwcmludCI6ICJlZWIzMzg4NjIxZjNmYzJkIiwgImlzb2xhdGFi"
    "bGVfcGVyX3NlZ21lbnQiOiA2LCAib3duX3RocmVhdHMiOiB7InNlZ19hbHBo"
    "YSI6IDE4LCAic2VnX2JldGEiOiAxNCwgInNlZ19kZWx0YSI6IDksICJzZWdf"
    "ZXBzaWxvbiI6IDEwLCAic2VnX2V0YSI6IDExLCAic2VnX2dhbW1hIjogMTEs"
    "ICJzZWdfemV0YSI6IDl9LCAicGFpcl9jb3VudCI6IDIxLCAicHJpb3JpdHlf"
    "bW9ub3RvbmljIjogdHJ1ZSwgInRyYW5zZmVyX2NoZWNrIjogeyJzZWdfYmV0"
    "YSI6IHsiaW5kZXgiOiAwLCAibWluX3ZhbHVlIjogOX19fQ=="
)


def _load_oracle():
    """Decode the verification oracle data."""
    return json.loads(base64.b64decode(_ORACLE_B64).decode())


def load_findings():
    """Load detection findings from JSONL file."""
    records = []
    with open(FINDINGS_FILE, "r") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_summary():
    """Load detection summary from JSON file."""
    with open(SUMMARY_FILE, "r") as fh:
        return json.load(fh)


# ============================================================
# TIER 1: Structural tests (always pass with buggy code)
# ============================================================


class TestTier1Structural:
    """Structural validation of detection output format."""

    def test_output_files_exist(self):
        """Both output files must be generated."""
        assert os.path.isfile(FINDINGS_FILE), "detection_findings.jsonl not found"
        assert os.path.isfile(SUMMARY_FILE), "detection_summary.json not found"

    def test_segment_count(self):
        """Detection must produce findings for exactly 7 segments."""
        findings = load_findings()
        assert len(findings) == 7

    def test_segment_ids(self):
        """All monitored segment IDs must be present."""
        findings = load_findings()
        ids = {f["segment_id"] for f in findings}
        expected = {
            "seg_alpha", "seg_beta", "seg_gamma", "seg_delta",
            "seg_epsilon", "seg_zeta", "seg_eta"
        }
        assert ids == expected

    def test_vector_dimensions(self):
        """Each finding must contain a 7-element threat vector."""
        findings = load_findings()
        for f in findings:
            assert len(f["threat_vector"]) == 7, (
                f"{f['segment_id']} has {len(f['threat_vector'])}-element vector"
            )

    def test_required_fields(self):
        """Each finding must contain all required fields."""
        findings = load_findings()
        required = {"segment_id", "threat_vector", "threat_total",
                    "isolatable_from", "triage_rank"}
        for f in findings:
            assert required.issubset(f.keys()), (
                f"{f['segment_id']} missing: {required - set(f.keys())}"
            )

    def test_summary_segment_count(self):
        """Summary must report correct segment count."""
        summary = load_summary()
        assert summary["segment_count"] == 7


# ============================================================
# TIER 2: Threat state tests (need Bug 1 fixed)
# ============================================================


class TestTier2ThreatState:
    """Threat vector correctness -- requires proper LATERAL handling."""

    def test_threat_after_lateral(self):
        """Segments with LATERAL events must reflect propagation contribution.

        Own threat component must match the verified oracle value.
        """
        oracle = _load_oracle()
        findings = load_findings()
        all_ids = sorted(f["segment_id"] for f in findings)

        seg_beta = next(f for f in findings if f["segment_id"] == "seg_beta")
        own_idx = all_ids.index("seg_beta")
        expected = oracle["own_threats"]["seg_beta"]
        actual = seg_beta["threat_vector"][own_idx]
        assert actual == expected, (
            f"seg_beta own threat expected {expected}, got {actual}. "
            f"LATERAL events must always attribute to the segment's own threat."
        )

    def test_lateral_propagation_transfer(self):
        """LATERAL must propagate threat intelligence from adjacent segments.

        The max absorption should transfer higher values from the adjacent
        segment's report into the local threat vector.
        """
        oracle = _load_oracle()
        findings = load_findings()
        seg_beta = next(f for f in findings if f["segment_id"] == "seg_beta")
        check = oracle["transfer_check"]["seg_beta"]
        actual = seg_beta["threat_vector"][check["index"]]
        assert actual >= check["min_value"], (
            f"seg_beta position[{check['index']}] expected >= "
            f"{check['min_value']}, got {actual}. "
            f"LATERAL must absorb adjacent segment's higher threat values."
        )

    def test_all_lateral_segments_correct(self):
        """All segments with LATERAL events must have correct own threats.

        Verifies each segment's own threat component matches the oracle.
        """
        oracle = _load_oracle()
        findings = load_findings()
        all_ids = sorted(f["segment_id"] for f in findings)

        for seg_id, expected_own in oracle["own_threats"].items():
            finding = next(f for f in findings if f["segment_id"] == seg_id)
            own_idx = all_ids.index(seg_id)
            actual = finding["threat_vector"][own_idx]
            assert actual == expected_own, (
                f"{seg_id} own threat expected {expected_own}, got {actual}."
            )


# ============================================================
# TIER 3: Isolation classification tests (need Bugs 2+3 fixed)
# ============================================================


class TestTier3Isolation:
    """Segment isolation classification -- requires correct predicate and priority."""

    def test_triage_ordering_by_total(self):
        """Triage must be ordered by total threat sum (ascending).

        The triage_order should be monotonically non-decreasing when
        mapped to threat_total values.
        """
        findings = load_findings()
        summary = load_summary()
        triage = summary["triage_order"]

        totals_in_order = []
        for seg in triage:
            f = next(r for r in findings if r["segment_id"] == seg)
            totals_in_order.append(f["threat_total"])

        for i in range(len(totals_in_order) - 1):
            assert totals_in_order[i] <= totals_in_order[i + 1], (
                f"Triage not sorted by total: position {i} has {totals_in_order[i]}, "
                f"position {i+1} has {totals_in_order[i+1]}. "
                f"Must use total threat sum for triage priority."
            )

    def test_isolation_pair_count(self):
        """All segment pairs should be isolatable.

        With correct threat vectors, no vector dominates another in the
        component-wise order, so all C(n,2) pairs can be safely isolated.
        """
        oracle = _load_oracle()
        summary = load_summary()
        assert summary["isolation_pair_count"] == oracle["pair_count"], (
            f"Expected {oracle['pair_count']} isolation pairs, "
            f"got {summary['isolation_pair_count']}. "
            f"Isolation requires mutual non-dominance (incomparability)."
        )

    def test_isolation_coverage(self):
        """Every segment must be isolatable from all other segments."""
        oracle = _load_oracle()
        findings = load_findings()
        expected = oracle["isolatable_per_segment"]
        for f in findings:
            actual = len(f["isolatable_from"])
            assert actual == expected, (
                f"{f['segment_id']} isolatable from {actual} segments, "
                f"expected {expected}."
            )


# ============================================================
# TIER 4: Full consistency tests (need ALL bugs fixed)
# ============================================================


class TestTier4Consistency:
    """Full detection consistency -- requires all bugs fixed."""

    def test_fingerprint(self):
        """State fingerprint must match the verified correct value."""
        oracle = _load_oracle()
        findings = load_findings()
        content = json.dumps(findings, sort_keys=True)
        fingerprint = hashlib.md5(content.encode()).hexdigest()[:16]
        assert fingerprint == oracle["fingerprint"], (
            f"Fingerprint mismatch: got {fingerprint}, "
            f"expected {oracle['fingerprint']}"
        )

    def test_cross_validation(self):
        """Summary metrics must be consistent with findings data."""
        findings = load_findings()
        summary = load_summary()

        total_isolatable = sum(len(f["isolatable_from"]) for f in findings)
        assert total_isolatable // 2 == summary["isolation_pair_count"], (
            f"Cross-validation: findings imply {total_isolatable // 2} pairs, "
            f"summary reports {summary['isolation_pair_count']}"
        )

        assert len(summary["triage_order"]) == 7
        assert summary["aggregate_threat"] == sum(f["threat_total"] for f in findings)
