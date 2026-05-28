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
LOG_FILE = "/app/runtime/data/thermal_log.txt"

# Precomputed verification constants derived from correct simulation
_VERIFICATION_SEED = "lattice_thermal_v2"
_EXPECTED_DIGEST = "2ebb5ffc5b5c4fd7"


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


def _count_events_for_node(node_id):
    """Count events of each type for a given node from the trace log."""
    counts = {"DIFFUSE": 0, "CONVECT": 0, "EQUILIBRATE": 0}
    with open(LOG_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            parts = [p.strip() for p in line.split("->")]
            if len(parts) == 4 and parts[1] == node_id:
                etype = parts[2]
                if etype in counts:
                    counts[etype] += 1
    return counts


def _compute_expected_own_energy(node_id):
    """Compute expected own-component energy by replaying events from trace.

    Replays only own-component relevant events:
    - DIFFUSE: own += 1
    - CONVECT: own += 2
    - EQUILIBRATE: own = max(own, peer_value_for_self) + 1
    """
    base = 3
    own = base
    with open(LOG_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            parts = [p.strip() for p in line.split("->")]
            if len(parts) != 4 or parts[1] != node_id:
                continue
            etype = parts[2]
            if etype == "DIFFUSE":
                own += 1
            elif etype == "CONVECT":
                own += 2
            elif etype == "EQUILIBRATE":
                # Parse peer state to get reported value for self
                state_str = parts[3].split("=", 1)[1]
                peer_state = {}
                for pair in state_str.split(";"):
                    k, v = pair.split(":")
                    peer_state[k.strip()] = int(v.strip())
                if node_id in peer_state:
                    own = max(own, peer_state[node_id])
                own += 1
    return own


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
        """Nodes' own energy must include EQUILIBRATE contribution.

        Each EQUILIBRATE event should contribute 1 unit to the node's own
        energy component, just like DIFFUSE. The own-component energy should
        equal BASE + DIFFUSE_count + 2*CONVECT_count + EQUILIBRATE_count.
        """
        records = load_state()
        alpha = next(r for r in records if r["node_id"] == "node_alpha")
        # node_alpha is index 0 in sorted node list
        own_energy = alpha["energy_vector"][0]
        expected = _compute_expected_own_energy("node_alpha")
        assert own_energy == expected, (
            f"node_alpha own energy expected {expected}, got {own_energy}. "
            f"EQUILIBRATE events must contribute to the node's own component."
        )

    def test_equilibrate_knowledge_transfer(self):
        """Node beta must absorb thermal knowledge from its EQUILIBRATE peer.

        The component-wise max operation should transfer higher values from
        the peer's reported state into the local vector.
        """
        records = load_state()
        beta = next(r for r in records if r["node_id"] == "node_beta")
        # node_alpha is index 0 in sorted node list
        # beta's EQUILIBRATE peer reports node_alpha:9, so beta[0] >= 9
        alpha_component = beta["energy_vector"][0]
        assert alpha_component >= 9, (
            f"node_beta's alpha-component expected >= 9, got {alpha_component}. "
            f"EQUILIBRATE must absorb peer's higher values via max."
        )

    def test_vector_sums_with_merges(self):
        """Nodes with EQUILIBRATE must have sums reflecting both absorbed
        knowledge AND the equilibration contribution to own component.

        For nodes with EQUILIBRATE, own_energy should match the formula:
        BASE + DIFFUSE_count + 2*CONVECT_count + EQUILIBRATE_count.
        The total sum will also include absorbed peer values.
        """
        records = load_state()
        # Verify multiple nodes with EQUILIBRATE have correct own component
        for rec in records:
            node_id = rec["node_id"]
            counts = _count_events_for_node(node_id)
            if counts["EQUILIBRATE"] > 0:
                expected_own = _compute_expected_own_energy(node_id)
                # Find own component index (sorted position of node_id)
                all_ids = sorted(r["node_id"] for r in records)
                own_idx = all_ids.index(node_id)
                actual_own = rec["energy_vector"][own_idx]
                assert actual_own == expected_own, (
                    f"{node_id} own energy expected {expected_own}, got {actual_own}. "
                    f"EQUILIBRATE must contribute to the node's own component."
                )


# ============================================================
# TIER 3: Thermal independence tests (need Bugs 2+3 fixed)
# ============================================================


class TestTier3Independence:
    """Thermal independence classification -- requires correct predicate and priority."""

    def test_priority_ordering_by_sum(self):
        """Priority must be ordered by total energy sum.

        The node with the lowest vector_sum should have priority_rank 0,
        and the node with the highest vector_sum should have the highest rank.
        """
        records = load_state()
        report = load_report()
        priority = report["priority_order"]

        # Get sums for first and last in priority
        first_node = priority[0]
        last_node = priority[-1]
        first_rec = next(r for r in records if r["node_id"] == first_node)
        last_rec = next(r for r in records if r["node_id"] == last_node)

        assert first_rec["vector_sum"] <= last_rec["vector_sum"], (
            f"Priority order wrong: first node {first_node} has sum "
            f"{first_rec['vector_sum']}, last node {last_node} has sum "
            f"{last_rec['vector_sum']}. First should have lowest sum."
        )

        # Verify full ordering is monotonically non-decreasing by sum
        sums_in_priority_order = []
        for node in priority:
            rec = next(r for r in records if r["node_id"] == node)
            sums_in_priority_order.append(rec["vector_sum"])

        for i in range(len(sums_in_priority_order) - 1):
            assert sums_in_priority_order[i] <= sums_in_priority_order[i + 1], (
                f"Priority not sorted by sum: position {i} has sum "
                f"{sums_in_priority_order[i]}, position {i+1} has sum "
                f"{sums_in_priority_order[i+1]}"
            )

    def test_independent_pair_count(self):
        """All node pairs should be thermally independent.

        With correct energy vectors, no node's vector dominates another's
        in the component-wise partial order. Therefore all C(7,2) = 21
        pairs should be classified as independent.
        """
        report = load_report()
        # C(7,2) = 21 total possible pairs
        max_pairs = 7 * 6 // 2
        assert report["independent_pair_count"] == max_pairs, (
            f"Expected {max_pairs} independent pairs, "
            f"got {report['independent_pair_count']}. "
            f"Independence requires mutual non-dominance in the partial order."
        )

    def test_independence_coverage(self):
        """Every node must be independent from all 6 other nodes.

        Since no energy vector dominates another in the correct output,
        each node should list all other nodes as independent neighbors.
        """
        records = load_state()
        num_nodes = len(records)
        for rec in records:
            neighbor_count = len(rec["independent_neighbors"])
            assert neighbor_count == num_nodes - 1, (
                f"{rec['node_id']} has {neighbor_count} independent neighbors, "
                f"expected {num_nodes - 1}."
            )


# ============================================================
# TIER 4: Full consistency tests (need ALL bugs fixed)
# ============================================================


class TestTier4Consistency:
    """Full simulation consistency -- requires all bugs to be fixed."""

    def test_digest(self):
        """State digest must match the verified correct value."""
        records = load_state()
        content = json.dumps(records, sort_keys=True)
        digest = hashlib.md5(content.encode()).hexdigest()[:16]
        assert digest == _EXPECTED_DIGEST, (
            f"Digest mismatch: got {digest}, expected {_EXPECTED_DIGEST}"
        )

    def test_cross_validation(self):
        """Report statistics must be consistent with state file contents."""
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
