"""
Tests for the lattice thermal diffusion simulation.
Validates structural output, energy state correctness, thermal independence
classification, and full simulation consistency.
"""

import json
import os
import sys
import hashlib

sys.path.insert(0, "/app/runtime")

STATE_FILE = "/app/runtime/thermal_state.jsonl"
REPORT_FILE = "/app/runtime/thermal_summary.json"


def load_state():
    """Load state records from JSONL file."""
    records = []
    with open(STATE_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_report():
    """Load summary report from JSON file."""
    with open(REPORT_FILE, "r") as f:
        return json.load(f)


# ============================================================
# TIER 1: Structural tests (always pass with buggy code)
# ============================================================


class TestTier1Structural:
    """Structural validation — output format and completeness."""

    def test_output_files_exist(self):
        """Both output files must exist after simulation."""
        assert os.path.isfile(STATE_FILE), "thermal_state.jsonl missing"
        assert os.path.isfile(REPORT_FILE), "thermal_summary.json missing"

    def test_node_count(self):
        """Simulation must produce records for exactly 7 lattice nodes."""
        records = load_state()
        assert len(records) == 7

    def test_node_ids(self):
        """All expected node IDs must be present."""
        records = load_state()
        node_ids = {r["node_id"] for r in records}
        expected = {
            "node_alpha", "node_beta", "node_gamma", "node_delta",
            "node_epsilon", "node_zeta", "node_eta"
        }
        assert node_ids == expected

    def test_events_per_node(self):
        """Each record must have a 7-element energy vector."""
        records = load_state()
        for rec in records:
            assert len(rec["energy_vector"]) == 7, (
                f"{rec['node_id']} has {len(rec['energy_vector'])}-element vector"
            )

    def test_required_fields(self):
        """Each state record must contain all required fields."""
        records = load_state()
        required = {"node_id", "energy_vector", "vector_sum",
                    "independent_neighbors", "priority_rank"}
        for rec in records:
            assert required.issubset(rec.keys()), (
                f"{rec['node_id']} missing fields: {required - set(rec.keys())}"
            )

    def test_total_event_count(self):
        """Report must contain correct total node count."""
        report = load_report()
        assert report["total_nodes"] == 7


# ============================================================
# TIER 2: Energy state tests (need Bug 1 fixed)
# ============================================================


class TestTier2EnergyState:
    """Energy vector correctness — requires proper EQUILIBRATE handling."""

    def test_energy_after_equilibrate(self):
        """Node alpha's own energy must include EQUILIBRATE contribution.

        node_alpha has 8 DIFFUSE (+8), 3 CONVECT (+6), and 1 EQUILIBRATE (+1).
        Own component should be BASE(3) + 8 + 6 + 1 = 18.
        """
        records = load_state()
        alpha = next(r for r in records if r["node_id"] == "node_alpha")
        # node_alpha is index 0 in sorted node list
        own_energy = alpha["energy_vector"][0]
        assert own_energy == 18, (
            f"node_alpha own energy expected 18, got {own_energy}. "
            f"EQUILIBRATE must increment the node's own component."
        )

    def test_equilibrate_knowledge_transfer(self):
        """Node beta must absorb node_alpha's energy via EQUILIBRATE.

        After beta's EQUILIBRATE with peer_state containing node_alpha:9,
        beta's vector[0] (alpha's slot) should be max(3, 9) = 9.
        """
        records = load_state()
        beta = next(r for r in records if r["node_id"] == "node_beta")
        # node_alpha is index 0 in sorted node list
        alpha_component = beta["energy_vector"][0]
        assert alpha_component == 9, (
            f"node_beta's alpha-component expected 9, got {alpha_component}"
        )

    def test_vector_sums_with_merges(self):
        """Nodes with EQUILIBRATE events must have higher sums than isolated nodes.

        node_beta (has EQUILIBRATE) should have sum 38.
        node_eta (no EQUILIBRATE) should have sum 29.
        """
        records = load_state()
        beta = next(r for r in records if r["node_id"] == "node_beta")
        eta = next(r for r in records if r["node_id"] == "node_eta")
        assert beta["vector_sum"] == 38, (
            f"node_beta sum expected 38, got {beta['vector_sum']}"
        )
        assert eta["vector_sum"] == 29, (
            f"node_eta sum expected 29, got {eta['vector_sum']}"
        )


# ============================================================
# TIER 3: Thermal independence tests (need Bugs 2+3 fixed)
# ============================================================


class TestTier3Independence:
    """Thermal independence classification — requires correct predicate and priority."""

    def test_priority_not_physical_time(self):
        """Priority must be by energy sum, not by event recency.

        Correct first (lowest sum): node_epsilon (sum=28)
        Correct last (highest sum): node_beta (sum=38)
        Buggy order uses last event sequence number instead.
        """
        report = load_report()
        priority = report["priority_order"]
        assert priority[0] == "node_epsilon", (
            f"First priority expected node_epsilon, got {priority[0]}"
        )
        assert priority[-1] == "node_beta", (
            f"Last priority expected node_beta, got {priority[-1]}"
        )

    def test_independent_pair_count(self):
        """Exactly 21 thermally independent pairs must be identified.

        With correct vectors (Bug 1 fixed) and correct independence predicate
        (Bug 2 fixed), all 21 pairs of 7 nodes are thermally independent
        since no node's vector dominates another's.
        """
        report = load_report()
        assert report["independent_pair_count"] == 21, (
            f"Expected 21 independent pairs, got {report['independent_pair_count']}. "
            f"Independence requires incomparability (neither dominates), not equality."
        )

    def test_independence_coverage(self):
        """Every node must have exactly 6 independent neighbors (all others).

        Since no energy vector dominates another, all pairs are independent.
        Each node should list all 6 other nodes as independent neighbors.
        """
        records = load_state()
        for rec in records:
            neighbor_count = len(rec["independent_neighbors"])
            assert neighbor_count == 6, (
                f"{rec['node_id']} has {neighbor_count} independent neighbors, "
                f"expected 6. All pairs should be independent."
            )


# ============================================================
# TIER 4: Full consistency tests (need ALL bugs fixed)
# ============================================================


class TestTier4Consistency:
    """Full simulation consistency — requires all bugs to be fixed."""

    def test_digest(self):
        """State digest must match the verified correct value.

        This is a fingerprint of the complete correct state including
        energy vectors, independence classifications, and priority ranks.
        """
        records = load_state()
        content = json.dumps(records, sort_keys=True)
        digest = hashlib.md5(content.encode()).hexdigest()[:16]
        assert digest == "2ebb5ffc5b5c4fd7", (
            f"Digest mismatch: got {digest}, expected 2ebb5ffc5b5c4fd7"
        )

    def test_cross_validation(self):
        """Report statistics must be consistent with state file contents.

        Validates that independent_pair_count in report matches actual
        pairs derivable from state records, and priority_order is consistent.
        """
        records = load_state()
        report = load_report()

        # Verify pair count matches state records
        total_independent = sum(
            len(r["independent_neighbors"]) for r in records
        )
        # Each pair counted twice (once from each side)
        assert total_independent // 2 == report["independent_pair_count"], (
            f"Cross-validation failed: state has {total_independent // 2} pairs, "
            f"report claims {report['independent_pair_count']}"
        )

        # Verify priority order length
        assert len(report["priority_order"]) == 7

        # Verify total energy
        state_total = sum(r["vector_sum"] for r in records)
        assert report["total_energy"] == state_total
