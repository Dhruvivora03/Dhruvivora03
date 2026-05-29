"""
Test suite for threat intelligence correlation pipeline.

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
                    f"Vector for {entry['segment_id']} has "
                    f"{len(entry['threat_vector'])} components, expected 7"
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

    def test_report_structure(self):
        """Report must contain segment_state, correlation_analysis, and digest entries."""
        report = load_jsonl(REPORT_PATH)
        types = {r.get("type") for r in report}
        assert "segment_state" in types, "Missing segment_state entries"
        assert "correlation_analysis" in types, "Missing correlation_analysis entry"
        assert "digest" in types, "Missing digest entry"
        analysis = [r for r in report if r["type"] == "correlation_analysis"]
        assert len(analysis[0]["triage_order"]) == 7


# ═══════════════════════════════════════════
# TIER 2: State value tests (need Bug 1 fixed)
# ═══════════════════════════════════════════


class TestTier2StateValues:
    """Threat vector correctness — requires proper CORRELATE increment timing."""

    def test_dmz_own_threat_after_correlate(self):
        """DMZ's own threat component must reflect correct CORRELATE processing.

        DMZ participates in 2 CORRELATE events plus 4 PROBE (+1 each) and
        2 BREACH (+2 each). The correlation increment must be applied after
        intelligence absorption to correctly sequence the causal update.
        """
        state = load_jsonl(STATE_PATH)
        dmz = next(s for s in state if s["segment_id"] == "dmz")
        # Sorted segments: bastion(0), core(1), dmz(2), edge(3), enclave(4), relay(5), vault(6)
        dmz_own = dmz["threat_vector"][2]
        assert dmz_own == 15, (
            f"DMZ own threat component is {dmz_own}, expected 15. "
            f"The CORRELATE self-increment must be applied after the merge "
            f"operation to correctly reflect the causal ordering of intelligence "
            f"acquisition followed by state update."
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

        DMZ (correlated) should have vector_sum >= 73 reflecting both
        correlation increments and absorbed intelligence from peers.
        """
        state = load_jsonl(STATE_PATH)
        dmz = next(s for s in state if s["segment_id"] == "dmz")
        relay = next(s for s in state if s["segment_id"] == "relay")
        assert dmz["vector_sum"] >= 73, (
            f"DMZ vector_sum is {dmz['vector_sum']}, expected >= 73. "
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

    def test_triage_order_by_severity(self):
        """Triage order must reflect total accumulated threat severity.

        The last segment in triage order should be the one with highest
        total threat level (vector sum), representing the most critical
        zone requiring immediate response attention.
        """
        report = load_jsonl(REPORT_PATH)
        analysis = next(r for r in report if r["type"] == "correlation_analysis")
        triage = analysis["triage_order"]
        # Correct last = dmz (highest sum=73)
        assert triage[-1] == "dmz", (
            f"Last triage segment is '{triage[-1]}', expected 'dmz' (highest threat). "
            f"Triage priority must order by total accumulated threat severity."
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
            f"Three pairs have dominance relationships and must not be "
            f"classified as isolated."
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
            ("dmz", "relay"), ("relay", "dmz"),
            ("dmz", "bastion"), ("bastion", "dmz"),
            ("dmz", "enclave"), ("enclave", "dmz"),
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
        expected = "4f6097112936e335"
        assert digest_entry["fingerprint"] == expected, (
            f"Digest mismatch: got '{digest_entry['fingerprint']}', "
            f"expected '{expected}'. This indicates one or more computation "
            f"errors in the pipeline."
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
                f"Vector mismatch for {sid}: "
                f"state={state_map[sid]['threat_vector']} "
                f"vs report={report_map[sid]['threat_vector']}"
            )
            assert state_map[sid]["vector_sum"] == report_map[sid]["vector_sum"], (
                f"Sum mismatch for {sid}: "
                f"state={state_map[sid]['vector_sum']} "
                f"vs report={report_map[sid]['vector_sum']}"
            )
