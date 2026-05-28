"""
Tests for the lattice thermal diffusion simulation.
Validates structural output, energy state correctness, thermal independence
classification, and full simulation consistency.
"""

import json
import os
import sys
import hashlib
import base64

sys.path.insert(0, "/app/runtime")

STATE_FILE = "/app/runtime/thermal_state.jsonl"
REPORT_FILE = "/app/runtime/thermal_summary.json"

# Verification oracle: base64-encoded expected values from a verified
# correct simulation run. Decode at runtime for comparison.
_ORACLE_B64 = (
    "eyJkaWdlc3QiOiAiMmViYjVmZmM1YjVjNGZkNyIsICJrbm93bGVkZ2VfdHJhbn"
    "NmZXIiOiB7Im5vZGVfYmV0YSI6IHsiaW5kZXgiOiAwLCAibWluX3ZhbHVlIjog"
    "OX19LCAibmVpZ2hib3JzX3Blcl9ub2RlIjogNiwgIm93bl9lbmVyZ2llcyI6IH"
    "sibm9kZV9hbHBoYSI6IDE4LCAibm9kZV9iZXRhIjogMTQsICJub2RlX2RlbHRh"
    "IjogOSwgIm5vZGVfZXBzaWxvbiI6IDEwLCAibm9kZV9ldGEiOiAxMSwgIm5vZG"
    "VfZ2FtbWEiOiAxMSwgIm5vZGVfemV0YSI6IDl9LCAicGFpcl9jb3VudCI6IDIx"
    "LCAicHJpb3JpdHlfbW9ub3RvbmljIjogdHJ1ZX0="
)


def _load_oracle():
    """Decode the verification oracle data."""
    return json.loads(base64.b64decode(_ORACLE_B64).decode())


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
    """Structural validation -- output format and completeness."""

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
    """Energy vector correctness -- requires proper EQUILIBRATE handling."""

    def test_energy_after_equilibrate(self):
        """Nodes that processed EQUILIBRATE must have correct own energy.

        The own-component energy must match the verified oracle value,
        which accounts for all event types including equilibration.
        """
        oracle = _load_oracle()
        records = load_state()
        all_ids = sorted(r["node_id"] for r in records)

        # Check node_alpha specifically (has EQUILIBRATE)
        alpha = next(r for r in records if r["node_id"] == "node_alpha")
        own_idx = all_ids.index("node_alpha")
        expected = oracle["own_energies"]["node_alpha"]
        actual = alpha["energy_vector"][own_idx]
        assert actual == expected, (
            f"node_alpha own energy expected {expected}, got {actual}. "
            f"EQUILIBRATE events must contribute to the node's own component."
        )

    def test_equilibrate_knowledge_transfer(self):
        """EQUILIBRATE must transfer thermal knowledge from the peer node.

        The component-wise max operation should absorb higher values from
        the peer's reported state into the local energy vector.
        """
        oracle = _load_oracle()
        records = load_state()
        beta = next(r for r in records if r["node_id"] == "node_beta")
        transfer = oracle["knowledge_transfer"]["node_beta"]
        actual = beta["energy_vector"][transfer["index"]]
        assert actual >= transfer["min_value"], (
            f"node_beta component[{transfer['index']}] expected >= "
            f"{transfer['min_value']}, got {actual}. "
            f"EQUILIBRATE must absorb peer's higher values via max."
        )

    def test_vector_sums_with_merges(self):
        """All nodes with EQUILIBRATE must have correct own-component values.

        Verifies that every node's own energy component matches the oracle,
        confirming proper handling of equilibration contributions.
        """
        oracle = _load_oracle()
        records = load_state()
        all_ids = sorted(r["node_id"] for r in records)

        for node_id, expected_own in oracle["own_energies"].items():
            rec = next(r for r in records if r["node_id"] == node_id)
            own_idx = all_ids.index(node_id)
            actual = rec["energy_vector"][own_idx]
            assert actual == expected_own, (
                f"{node_id} own energy expected {expected_own}, got {actual}."
            )


# ============================================================
# TIER 3: Thermal independence tests (need Bugs 2+3 fixed)
# ============================================================


class TestTier3Independence:
    """Thermal independence classification -- requires correct predicate and priority."""

    def test_priority_ordering_by_sum(self):
        """Priority must be ordered by total energy sum (ascending).

        The priority_order in the report should be monotonically
        non-decreasing when mapped to vector_sum values.
        """
        records = load_state()
        report = load_report()
        priority = report["priority_order"]

        sums_in_order = []
        for node in priority:
            rec = next(r for r in records if r["node_id"] == node)
            sums_in_order.append(rec["vector_sum"])

        for i in range(len(sums_in_order) - 1):
            assert sums_in_order[i] <= sums_in_order[i + 1], (
                f"Priority not sorted by sum: position {i} has sum "
                f"{sums_in_order[i]}, position {i+1} has sum "
                f"{sums_in_order[i+1]}. Must use total energy sum."
            )

    def test_independent_pair_count(self):
        """All node pairs should be classified as thermally independent.

        With correct energy vectors, no vector dominates another in the
        component-wise partial order, so all C(n,2) pairs are independent.
        """
        oracle = _load_oracle()
        report = load_report()
        assert report["independent_pair_count"] == oracle["pair_count"], (
            f"Expected {oracle['pair_count']} independent pairs, "
            f"got {report['independent_pair_count']}. "
            f"Independence requires mutual non-dominance in the partial order."
        )

    def test_independence_coverage(self):
        """Every node must be independent from all other nodes.

        Each node should list all other nodes as independent neighbors.
        """
        oracle = _load_oracle()
        records = load_state()
        expected_neighbors = oracle["neighbors_per_node"]
        for rec in records:
            actual = len(rec["independent_neighbors"])
            assert actual == expected_neighbors, (
                f"{rec['node_id']} has {actual} independent neighbors, "
                f"expected {expected_neighbors}."
            )


# ============================================================
# TIER 4: Full consistency tests (need ALL bugs fixed)
# ============================================================


class TestTier4Consistency:
    """Full simulation consistency -- requires all bugs to be fixed."""

    def test_digest(self):
        """State digest must match the verified correct value."""
        oracle = _load_oracle()
        records = load_state()
        content = json.dumps(records, sort_keys=True)
        digest = hashlib.md5(content.encode()).hexdigest()[:16]
        assert digest == oracle["digest"], (
            f"Digest mismatch: got {digest}, expected {oracle['digest']}"
        )

    def test_cross_validation(self):
        """Report statistics must be consistent with state file contents."""
        records = load_state()
        report = load_report()

        # Verify pair count matches state records
        total_independent = sum(
            len(r["independent_neighbors"]) for r in records
        )
        assert total_independent // 2 == report["independent_pair_count"], (
            f"Cross-validation failed: state has {total_independent // 2} pairs, "
            f"report claims {report['independent_pair_count']}"
        )

        # Verify priority order length
        assert len(report["priority_order"]) == 7

        # Verify total energy
        state_total = sum(r["vector_sum"] for r in records)
        assert report["total_energy"] == state_total
