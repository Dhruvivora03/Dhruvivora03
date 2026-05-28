"""
Test suite for threat intelligence correlation simulation.

Validates correctness of the correlation pipeline across four tiers:
- Tier 1 (structural): output file existence, segment counts, field integrity
- Tier 2 (state values): threat vector computations after correlation events
- Tier 3 (pair classification): isolated pair detection and triage ordering
- Tier 4 (full consistency): digest verification and cross-validation
"""

import json
import os
import sys

sys.path.insert(0, "/app/runtime")

STATE_PATH = "/app/runtime/segment_state.jsonl"
REPORT_PATH = "/app/runtime/threat_assessment.jsonl"


def load_jsonl(path):
    lines = []
    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if line:
                lines.append(json.loads(line))
    return lines


# ═══════════════════════════════════════════
# TIER 1: Structural tests (always pass)
# ═══════════════════════════════════════════


class TestTier1Structural:
    """Basic structural validation — these pass regardless of computation bugs."""

    def test_output_files_exist(self):
        """Both state and report files must be generated."""
        assert os.path.isfile(STATE_PATH), f"Missing state file: {STATE_PATH}"
        assert os.path.isfile(REPORT_PATH), f"Missing report file: {REPORT_PATH}"

    def test_segment_count(self):
        """Correlation must track exactly 7 network segments."""
        state = load_jsonl(STATE_PATH)
        segment_entries = [s for s in state if "segment_id" in s]
        assert len(segment_entries) == 7, f"Expected 7 segments, got {len(segment_entries)}"

    def test_segment_ids(self):
        """All 7 expected segment identifiers must be present."""
        state = load_jsonl(STATE_PATH)
        ids = {s["segment_id"] for s in state if "segment_id" in s}
        expected = {"dmz", "vault", "core", "edge", "relay", "bastion", "enclave"}
        assert ids == expected, f"Segment ID mismatch: {ids} != {expected}"

    def test_vector_dimensions(self):
        """Each threat vector must have exactly 7 components."""
        state = load_jsonl(STATE_PATH)
        for entry in state:
            if "threat_vector" in entry:
                assert len(entry["threat_vector"]) == 7, (
                    f"Vector for {entry['segment_id']} has {len(entry['threat_vector'])} "
                    f"components, expected 7"
                )

    def test_required_fields(self):
        """Each state entry must contain segment_id, threat_vector, vector_sum."""
        state = load_jsonl(STATE_PATH)
        required = {"segment_id", "threat_vector", "vector_sum"}
        for entry in state:
            assert required.issubset(entry.keys()), (
                f"Missing fields in {entry.get('segment_id', '?')}: "
                f"{required - set(entry.keys())}"
            )

    def test_total_event_count(self):
        """Report must reference the correct number of monitored segments."""
        report = load_jsonl(REPORT_PATH)
        analysis = [r for r in report if r.get("type") == "correlation_analysis"]
        assert len(analysis) == 1, "Expected exactly one correlation_analysis entry"
        # Verify triage_order has all 7 segments
        assert len(analysis[0]["triage_order"]) == 7


# ═══════════════════════════════════════════
# TIER 2: State value tests (need Bug 1 fixed)
# ═══════════════════════════════════════════


class TestTier2StateValues:
    """Threat vector correctness — requires proper CORRELATE increment logic."""

    def test_dmz_own_threat_after_correlate(self):
        """DMZ's own threat component must reflect CORRELATE participation.

        DMZ participates in 2 CORRELATE events plus 4 PROBE (+1 each) and
        2 BREACH (+2 each) events. Own component must equal
        BASE(3) + 4*1 + 2*2 + correlation_increments = expected value.
        """
        state = load_jsonl(STATE_PATH)
        dmz = next(s for s in state if s["segment_id"] == "dmz")
        # Sorted segments: bastion(0), core(1), dmz(2), edge(3), enclave(4), relay(5), vault(6)
        dmz_own = dmz["threat_vector"][2]
        assert dmz_own == 14, (
            f"DMZ own threat component is {dmz_own}, expected 14. "
            f"CORRELATE events must increment the segment's own threat counter."
        )

    def test_correlate_knowledge_transfer(self):
        """Vault must absorb DMZ's threat level from CORRELATE exchange.

        When vault correlates with a neighbor reporting dmz:9, vault's
        dmz-component must reflect that absorbed intelligence.
        """
        state = load_jsonl(STATE_PATH)
        vault = next(s for s in state if s["segment_id"] == "vault")
        # vault's dmz-component (index 2 in sorted order)
        vault_dmz_component = vault["threat_vector"][2]
        assert vault_dmz_component == 9, (
            f"Vault's dmz-component is {vault_dmz_component}, expected 9. "
            f"CORRELATE must propagate neighbor intelligence via component-wise max."
        )

    def test_correlated_vs_uncorrelated_sums(self):
        """Segments with CORRELATE events must have higher sums than uncorrelated ones.

        DMZ (correlated) should have vector_sum > relay (uncorrelated) by a
        significant margin reflecting both correlation increments and absorbed intel.
        """
        state = load_jsonl(STATE_PATH)
        dmz = next(s for s in state if s["segment_id"] == "dmz")
        relay = next(s for s in state if s["segment_id"] == "relay")
        # DMZ (heavily correlated): correct sum = 72
        # Relay (no correlation): sum = 27
        assert dmz["vector_sum"] >= 72, (
            f"DMZ vector_sum is {dmz['vector_sum']}, expected >= 72. "
            f"Correlated segments must accumulate threat from intelligence sharing."
        )
        assert relay["vector_sum"] == 27, (
            f"Relay vector_sum is {relay['vector_sum']}, expected 27."
        )


# ═══════════════════════════════════════════
# TIER 3: Pair classification (need Bugs 2+3 fixed)
# ═══════════════════════════════════════════


class TestTier3PairClassification:
    """Isolated pair detection and triage ordering."""

    def test_triage_order_not_temporal(self):
        """Triage order must NOT follow event recency.

        The last segment in triage order should be the one with highest
        total threat, not the one with most recent activity timestamp.
        """
        report = load_jsonl(REPORT_PATH)
        analysis = next(r for r in report if r["type"] == "correlation_analysis")
        triage = analysis["triage_order"]
        # Correct last = dmz (highest sum=72)
        # Buggy last = enclave (most recent event at seq 45)
        assert triage[-1] == "dmz", (
            f"Last triage segment is '{triage[-1]}', expected 'dmz' (highest threat). "
            f"Triage priority must order by total accumulated threat, not event recency."
        )

    def test_exact_isolated_pair_count(self):
        """Exactly 18 segment pairs must be classified as isolated.

        With 7 segments there are 21 possible pairs. DMZ dominates relay,
        bastion, and enclave, yielding 21 - 3 = 18 isolated (incomparable) pairs.
        """
        report = load_jsonl(REPORT_PATH)
        analysis = next(r for r in report if r["type"] == "correlation_analysis")
        count = analysis["isolated_count"]
        assert count == 18, (
            f"Isolated pair count is {count}, expected 18. "
            f"Three pairs have dominance relationships and must not be classified as isolated."
        )

    def test_no_dominated_pairs_in_isolated(self):
        """Isolated pairs must not include any dominance relationships.

        DMZ dominates relay, bastion, and enclave — these pairs must be
        excluded from the isolated set. The isolated set must only contain
        pairs where neither segment's vector dominates the other.
        """
        report = load_jsonl(REPORT_PATH)
        analysis = next(r for r in report if r["type"] == "correlation_analysis")
        pairs = [tuple(p) for p in analysis["isolated_pairs"]]
        # These pairs have dominance and must NOT appear
        forbidden = [
            ("dmz", "relay"),
            ("dmz", "bastion"),
            ("dmz", "enclave"),
            ("relay", "dmz"),
            ("bastion", "dmz"),
            ("enclave", "dmz"),
        ]
        for pair in forbidden:
            assert pair not in pairs, (
                f"Pair {pair} has a dominance relationship and must not be isolated."
            )
        # Verify some legitimate pairs ARE present
        assert ("vault", "relay") in pairs or ("relay", "vault") in pairs, (
            "Expected vault-relay to be isolated (incomparable vectors)."
        )


# ═══════════════════════════════════════════
# TIER 4: Full consistency (need ALL bugs fixed)
# ═══════════════════════════════════════════


class TestTier4Consistency:
    """End-to-end integrity — requires all bugs to be fixed."""

    def test_report_digest(self):
        """Report fingerprint must match the canonical correct digest.

        This validates the entire pipeline: correct threat computation,
        correct pair classification, and correct triage ordering all
        contribute to the final digest value.
        """
        report = load_jsonl(REPORT_PATH)
        digest_entry = next(r for r in report if r["type"] == "digest")
        expected = "9f83c0f249d4334c"
        assert digest_entry["fingerprint"] == expected, (
            f"Digest mismatch: got '{digest_entry['fingerprint']}', expected '{expected}'. "
            f"This indicates one or more computation errors in the pipeline."
        )

    def test_state_report_cross_validation(self):
        """State file threat vectors must exactly match report entries.

        Cross-validates that the state file and threat assessment report
        contain consistent threat vector data for all segments.
        """
        state = load_jsonl(STATE_PATH)
        report = load_jsonl(REPORT_PATH)

        state_map = {s["segment_id"]: s for s in state if "segment_id" in s}
        report_segments = [r for r in report if r.get("type") == "segment_state"]
        report_map = {r["segment_id"]: r for r in report_segments}

        assert len(state_map) == len(report_map) == 7

        for sid in state_map:
            assert sid in report_map, f"Segment {sid} missing from report"
            assert state_map[sid]["threat_vector"] == report_map[sid]["threat_vector"], (
                f"Vector mismatch for {sid}: state={state_map[sid]['threat_vector']} "
                f"vs report={report_map[sid]['threat_vector']}"
            )
            assert state_map[sid]["vector_sum"] == report_map[sid]["vector_sum"], (
                f"Sum mismatch for {sid}: state={state_map[sid]['vector_sum']} "
                f"vs report={report_map[sid]['vector_sum']}"
            )
