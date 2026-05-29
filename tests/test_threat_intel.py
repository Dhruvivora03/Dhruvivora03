"""
Test suite for threat intelligence correlation pipeline.
14 tests across 4 difficulty tiers.
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


class TestTier1Structural:

    def test_output_files_exist(self):
        assert os.path.isfile(STATE_PATH), f"Missing: {STATE_PATH}"
        assert os.path.isfile(REPORT_PATH), f"Missing: {REPORT_PATH}"

    def test_segment_count(self):
        state = load_jsonl(STATE_PATH)
        assert len([s for s in state if "segment_id" in s]) == 7

    def test_segment_ids(self):
        state = load_jsonl(STATE_PATH)
        ids = {s["segment_id"] for s in state if "segment_id" in s}
        assert ids == {"dmz", "vault", "core", "edge", "relay", "bastion", "enclave"}

    def test_vector_dimensions(self):
        state = load_jsonl(STATE_PATH)
        for entry in state:
            if "threat_vector" in entry:
                assert len(entry["threat_vector"]) == 7

    def test_required_fields(self):
        state = load_jsonl(STATE_PATH)
        for entry in state:
            assert {"segment_id", "threat_vector", "vector_sum"}.issubset(entry.keys())

    def test_report_structure(self):
        report = load_jsonl(REPORT_PATH)
        types = {r.get("type") for r in report}
        assert "segment_state" in types
        assert "correlation_analysis" in types
        assert "digest" in types


class TestTier2StateValues:

    def test_dmz_own_threat_after_correlate(self):
        state = load_jsonl(STATE_PATH)
        dmz = next(s for s in state if s["segment_id"] == "dmz")
        # Sorted: bastion(0), core(1), dmz(2), edge(3), enclave(4), relay(5), vault(6)
        dmz_own = dmz["threat_vector"][2]
        assert dmz_own == 14, (
            f"DMZ own threat is {dmz_own}, expected 14. "
            f"CORRELATE events must increment the segment's own component."
        )

    def test_correlate_knowledge_transfer(self):
        state = load_jsonl(STATE_PATH)
        vault = next(s for s in state if s["segment_id"] == "vault")
        vault_dmz = vault["threat_vector"][2]
        assert vault_dmz == 9, (
            f"Vault dmz-component is {vault_dmz}, expected 9."
        )

    def test_correlated_vs_uncorrelated_sums(self):
        state = load_jsonl(STATE_PATH)
        dmz = next(s for s in state if s["segment_id"] == "dmz")
        relay = next(s for s in state if s["segment_id"] == "relay")
        assert dmz["vector_sum"] >= 72, (
            f"DMZ sum is {dmz['vector_sum']}, expected >= 72."
        )
        assert relay["vector_sum"] == 27


class TestTier3PairClassification:

    def test_triage_order_by_severity(self):
        report = load_jsonl(REPORT_PATH)
        analysis = next(r for r in report if r["type"] == "correlation_analysis")
        triage = analysis["triage_order"]
        assert triage[-1] == "dmz", (
            f"Last triage is '{triage[-1]}', expected 'dmz' (highest sum)."
        )

    def test_exact_isolated_pair_count(self):
        report = load_jsonl(REPORT_PATH)
        analysis = next(r for r in report if r["type"] == "correlation_analysis")
        assert analysis["isolated_count"] == 14, (
            f"Isolated count is {analysis['isolated_count']}, expected 14."
        )

    def test_no_dominated_pairs_in_isolated(self):
        report = load_jsonl(REPORT_PATH)
        analysis = next(r for r in report if r["type"] == "correlation_analysis")
        pairs = [tuple(p) for p in analysis["isolated_pairs"]]
        forbidden = [("dmz", "relay"), ("dmz", "bastion"), ("dmz", "enclave"),
                     ("core", "relay"), ("core", "enclave"),
                     ("bastion", "relay"), ("bastion", "enclave")]
        for pair in forbidden:
            assert pair not in pairs and tuple(reversed(pair)) not in pairs, (
                f"Pair {pair} has dominance and must not be isolated."
            )
        assert ("vault", "relay") in pairs or ("relay", "vault") in pairs


class TestTier4Consistency:

    def test_report_digest(self):
        report = load_jsonl(REPORT_PATH)
        digest_entry = next(r for r in report if r["type"] == "digest")
        assert digest_entry["fingerprint"] == "59cb34cecde525ae", (
            f"Digest: got '{digest_entry['fingerprint']}', expected '59cb34cecde525ae'."
        )

    def test_state_report_cross_validation(self):
        state = load_jsonl(STATE_PATH)
        report = load_jsonl(REPORT_PATH)
        state_map = {s["segment_id"]: s for s in state}
        report_map = {r["segment_id"]: r for r in report if r.get("type") == "segment_state"}
        assert len(state_map) == len(report_map) == 7
        for sid in state_map:
            assert state_map[sid]["threat_vector"] == report_map[sid]["threat_vector"]
            assert state_map[sid]["vector_sum"] == report_map[sid]["vector_sum"]
