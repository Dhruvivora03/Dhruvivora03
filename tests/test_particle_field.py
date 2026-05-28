"""
Test suite for particle field energy dissipation simulation.

Validates correctness of the simulation pipeline across four tiers:
- Tier 1 (structural): output file existence, entity counts, field integrity
- Tier 2 (state values): energy vector computations after coupling events
- Tier 3 (pair classification): decoupled pair detection and shutdown ordering
- Tier 4 (full consistency): digest verification and cross-validation
"""

import json
import os
import sys

sys.path.insert(0, "/app/runtime")

STATE_PATH = "/app/runtime/field_state.jsonl"
REPORT_PATH = "/app/runtime/stability_report.jsonl"


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

    def test_particle_count(self):
        """Simulation must track exactly 7 particles."""
        state = load_jsonl(STATE_PATH)
        particle_entries = [s for s in state if "particle_id" in s]
        assert len(particle_entries) == 7, f"Expected 7 particles, got {len(particle_entries)}"

    def test_particle_ids(self):
        """All 7 expected particle identifiers must be present."""
        state = load_jsonl(STATE_PATH)
        ids = {s["particle_id"] for s in state if "particle_id" in s}
        expected = {"alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta"}
        assert ids == expected, f"Particle ID mismatch: {ids} != {expected}"

    def test_vector_dimensions(self):
        """Each energy vector must have exactly 7 components."""
        state = load_jsonl(STATE_PATH)
        for entry in state:
            if "energy_vector" in entry:
                assert len(entry["energy_vector"]) == 7, (
                    f"Vector for {entry['particle_id']} has {len(entry['energy_vector'])} "
                    f"components, expected 7"
                )

    def test_required_fields(self):
        """Each state entry must contain particle_id, energy_vector, vector_sum."""
        state = load_jsonl(STATE_PATH)
        required = {"particle_id", "energy_vector", "vector_sum"}
        for entry in state:
            assert required.issubset(entry.keys()), (
                f"Missing fields in {entry.get('particle_id', '?')}: "
                f"{required - set(entry.keys())}"
            )

    def test_total_event_count(self):
        """Report must reference the correct total number of simulation events."""
        report = load_jsonl(REPORT_PATH)
        analysis = [r for r in report if r.get("type") == "field_analysis"]
        assert len(analysis) == 1, "Expected exactly one field_analysis entry"
        # Verify shutdown_order has all 7 particles
        assert len(analysis[0]["shutdown_order"]) == 7


# ═══════════════════════════════════════════
# TIER 2: State value tests (need Bug 1 fixed)
# ═══════════════════════════════════════════


class TestTier2StateValues:
    """Energy vector correctness — requires proper COUPLE increment logic."""

    def test_alpha_own_energy_after_couple(self):
        """Alpha's own energy component must reflect COUPLE participation.

        Alpha participates in 2 COUPLE events plus 5 DRIFT (+1 each) and
        2 COLLIDE (+2 each) events. Own component must equal
        BASE(3) + 5*1 + 2*2 + coupling_increments = expected value.
        """
        state = load_jsonl(STATE_PATH)
        alpha = next(s for s in state if s["particle_id"] == "alpha")
        # Sorted particles: alpha(0), beta(1), delta(2), epsilon(3), eta(4), gamma(5), zeta(6)
        alpha_own = alpha["energy_vector"][0]
        assert alpha_own == 14, (
            f"Alpha own energy component is {alpha_own}, expected 14. "
            f"COUPLE events must increment the particle's own dissipation counter."
        )

    def test_couple_knowledge_transfer(self):
        """Beta must absorb alpha's energy level from COUPLE synchronization.

        When beta couples with a neighbor reporting alpha:9, beta's
        alpha-component must reflect that absorbed knowledge.
        """
        state = load_jsonl(STATE_PATH)
        beta = next(s for s in state if s["particle_id"] == "beta")
        # beta's alpha-component (index 0)
        beta_alpha_component = beta["energy_vector"][0]
        assert beta_alpha_component == 9, (
            f"Beta's alpha-component is {beta_alpha_component}, expected 9. "
            f"COUPLE must propagate neighbor knowledge via component-wise max."
        )

    def test_coupled_vs_uncoupled_sums(self):
        """Particles with COUPLE events must have higher sums than uncoupled ones.

        Alpha (coupled) should have vector_sum > epsilon (uncoupled) by a
        significant margin reflecting both coupling increments and absorbed knowledge.
        """
        state = load_jsonl(STATE_PATH)
        alpha = next(s for s in state if s["particle_id"] == "alpha")
        epsilon = next(s for s in state if s["particle_id"] == "epsilon")
        # Alpha (heavily coupled): correct sum = 72
        # Epsilon (no coupling): sum = 27
        assert alpha["vector_sum"] >= 72, (
            f"Alpha vector_sum is {alpha['vector_sum']}, expected >= 72. "
            f"Coupled particles must accumulate energy from synchronization."
        )
        assert epsilon["vector_sum"] == 27, (
            f"Epsilon vector_sum is {epsilon['vector_sum']}, expected 27."
        )


# ═══════════════════════════════════════════
# TIER 3: Pair classification (need Bugs 2+3 fixed)
# ═══════════════════════════════════════════


class TestTier3PairClassification:
    """Decoupled pair detection and shutdown ordering."""

    def test_shutdown_order_not_temporal(self):
        """Shutdown order must NOT follow event recency.

        The first particle in shutdown order should be the one with lowest
        total energy, not the one with earliest/latest activity timestamp.
        """
        report = load_jsonl(REPORT_PATH)
        analysis = next(r for r in report if r["type"] == "field_analysis")
        shutdown = analysis["shutdown_order"]
        # Correct first = epsilon (lowest sum=27), correct last = alpha (highest sum=72)
        # Buggy first = epsilon (happens to be same), but last should be alpha not eta
        assert shutdown[0] == "epsilon", (
            f"First shutdown particle is '{shutdown[0]}', expected 'epsilon' (lowest energy)."
        )
        assert shutdown[-1] == "alpha", (
            f"Last shutdown particle is '{shutdown[-1]}', expected 'alpha' (highest energy). "
            f"Shutdown priority must order by total dissipated energy, not event recency."
        )

    def test_exact_decoupled_pair_count(self):
        """Exactly 19 particle pairs must be classified as decoupled.

        With 7 particles there are 21 possible pairs. Alpha dominates both
        epsilon and eta, yielding 21 - 2 = 19 decoupled (incomparable) pairs.
        """
        report = load_jsonl(REPORT_PATH)
        analysis = next(r for r in report if r["type"] == "field_analysis")
        count = analysis["decoupled_count"]
        assert count == 19, (
            f"Decoupled pair count is {count}, expected 19. "
            f"Two pairs have dominance relationships and must not be classified as decoupled."
        )

    def test_no_dominated_pairs_in_decoupled(self):
        """Decoupled pairs must not include any dominance relationships.

        Alpha dominates epsilon and eta — these pairs must be excluded
        from the decoupled set. The decoupled set must only contain pairs
        where neither particle's vector dominates the other.
        """
        report = load_jsonl(REPORT_PATH)
        analysis = next(r for r in report if r["type"] == "field_analysis")
        pairs = [tuple(p) for p in analysis["decoupled_pairs"]]
        # These pairs have dominance and must NOT appear
        forbidden = [
            ("alpha", "epsilon"),
            ("alpha", "eta"),
            ("epsilon", "alpha"),
            ("eta", "alpha"),
        ]
        for pair in forbidden:
            assert pair not in pairs, (
                f"Pair {pair} has a dominance relationship and must not be decoupled."
            )
        # Verify some legitimate pairs ARE present
        assert ("beta", "epsilon") in pairs or ("epsilon", "beta") in pairs, (
            "Expected beta-epsilon to be decoupled (incomparable vectors)."
        )


# ═══════════════════════════════════════════
# TIER 4: Full consistency (need ALL bugs fixed)
# ═══════════════════════════════════════════


class TestTier4Consistency:
    """End-to-end integrity — requires all bugs to be fixed."""

    def test_report_digest(self):
        """Report fingerprint must match the canonical correct digest.

        This validates the entire pipeline: correct energy computation,
        correct pair classification, and correct shutdown ordering all
        contribute to the final digest value.
        """
        report = load_jsonl(REPORT_PATH)
        digest_entry = next(r for r in report if r["type"] == "digest")
        expected = "39e8b5fd76520962"
        assert digest_entry["fingerprint"] == expected, (
            f"Digest mismatch: got '{digest_entry['fingerprint']}', expected '{expected}'. "
            f"This indicates one or more computation errors in the pipeline."
        )

    def test_state_report_cross_validation(self):
        """State file energy vectors must exactly match report entries.

        Cross-validates that the state file and stability report contain
        consistent energy vector data for all particles.
        """
        state = load_jsonl(STATE_PATH)
        report = load_jsonl(REPORT_PATH)

        state_map = {s["particle_id"]: s for s in state if "particle_id" in s}
        report_particles = [r for r in report if r.get("type") == "particle_state"]
        report_map = {r["particle_id"]: r for r in report_particles}

        assert len(state_map) == len(report_map) == 7

        for pid in state_map:
            assert pid in report_map, f"Particle {pid} missing from report"
            assert state_map[pid]["energy_vector"] == report_map[pid]["energy_vector"], (
                f"Vector mismatch for {pid}: state={state_map[pid]['energy_vector']} "
                f"vs report={report_map[pid]['energy_vector']}"
            )
            assert state_map[pid]["vector_sum"] == report_map[pid]["vector_sum"], (
                f"Sum mismatch for {pid}: state={state_map[pid]['vector_sum']} "
                f"vs report={report_map[pid]['vector_sum']}"
            )
