"""
Test suite for particle collision simulation pipeline.

Validates simulation correctness across four tiers:
  Tier 1 (6 tests): Structural validation — output existence and format
  Tier 2 (3 tests): Momentum state values — per-particle vector correctness
  Tier 3 (3 tests): Trajectory classification — pair independence and priority
  Tier 4 (2 tests): Full consistency — digest and cross-validation
"""

import json
import os
import sys

sys.path.insert(0, "/app/runtime")

STATE_FILE = "/app/runtime/simulation_state.jsonl"
REPORT_FILE = "/app/runtime/trajectory_report.json"

EXPECTED_PARTICLES = [
    "particle_alpha",
    "particle_beta",
    "particle_delta",
    "particle_epsilon",
    "particle_eta",
    "particle_gamma",
    "particle_zeta",
]

TOTAL_EVENTS = 45
EVENTS_PER_PARTICLE = {
    "particle_alpha": 9,
    "particle_beta": 7,
    "particle_gamma": 5,
    "particle_delta": 6,
    "particle_epsilon": 6,
    "particle_zeta": 6,
    "particle_eta": 6,
}


def load_state():
    """Load simulation state from JSONL file."""
    records = []
    with open(STATE_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_report():
    """Load trajectory report from JSON file."""
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

    def test_particle_count(self):
        """Simulation must track exactly 7 particles."""
        report = load_report()
        assert report["simulation_summary"]["particle_count"] == 7

    def test_particle_ids(self):
        """All expected particle IDs must be present in report."""
        report = load_report()
        particles = sorted(report["simulation_summary"]["particles"])
        assert particles == EXPECTED_PARTICLES

    def test_events_per_particle(self):
        """Event distribution must match trace file."""
        state = load_state()
        summary = None
        for record in state:
            if record["type"] == "event_summary":
                summary = record
                break
        assert summary is not None, "No event_summary record in state file"
        for pid, expected_count in EVENTS_PER_PARTICLE.items():
            actual = summary["per_particle"].get(pid, 0)
            assert actual == expected_count, (
                f"{pid}: expected {expected_count} events, got {actual}"
            )

    def test_required_fields(self):
        """Each particle state record must have required fields."""
        state = load_state()
        particle_records = [r for r in state if r["type"] == "particle_state"]
        for record in particle_records:
            assert "particle_id" in record
            assert "momentum_vector" in record
            assert "own_momentum" in record
            assert len(record["momentum_vector"]) == 7

    def test_total_event_count(self):
        """Total event count must equal 45."""
        state = load_state()
        summary = None
        for record in state:
            if record["type"] == "event_summary":
                summary = record
                break
        assert summary is not None
        assert summary["total_events"] == TOTAL_EVENTS


# ═══════════════════════════════════════════════════════════════
# TIER 2: Momentum state values (need Bug 1 fixed)
# ═══════════════════════════════════════════════════════════════


class TestTier2MomentumState:
    """Tests that validate momentum vector correctness after collision."""

    def test_momentum_after_collide(self):
        """Particle alpha's own momentum must be 15 after COLLIDE + subsequent events.

        Alpha has 9 events: DRIFT(+1) + THRUST(+2) + DRIFT(+1) + COLLIDE(+1) +
        DRIFT(+1) + THRUST(+2) + DRIFT(+1) + DRIFT(+1) + THRUST(+2) = BASE(3) + 12 = 15.
        If COLLIDE does not increment, own momentum is only 14.
        """
        state = load_state()
        for record in state:
            if record["type"] == "particle_state" and record["particle_id"] == "particle_alpha":
                assert record["own_momentum"] == 15, (
                    f"particle_alpha own_momentum: expected 15, got {record['own_momentum']}. "
                    f"COLLIDE events must increment the particle's own momentum component."
                )
                return
        assert False, "particle_alpha state record not found"

    def test_collide_knowledge_transfer(self):
        """Particle beta must absorb alpha's momentum via COLLIDE peer_state.

        Beta collides with peer_state showing alpha:7. After absorption,
        beta's vector at index 0 (alpha's position) should be 7 (max of BASE=3, incoming=7).
        This tests the merge/absorption logic independent of self-increment.
        """
        state = load_state()
        for record in state:
            if record["type"] == "particle_state" and record["particle_id"] == "particle_beta":
                # Beta's vector at alpha's index (index 0) should be 7
                assert record["momentum_vector"][0] == 7, (
                    f"particle_beta vector[0]: expected 7 (absorbed from alpha via COLLIDE), "
                    f"got {record['momentum_vector'][0]}"
                )
                return
        assert False, "particle_beta state record not found"

    def test_vector_sums_with_collide(self):
        """Particles with COLLIDE events must have higher vector sums than non-colliders.

        Colliding particles (alpha, beta, gamma, delta) accumulate extra momentum
        from the collision event itself. Their vector sums must exceed those of
        non-colliding particles (epsilon, eta, zeta) which only have sum=29.
        """
        report = load_report()
        ms = report["momentum_state"]

        # Non-colliders have sum=29 (BASE*7 + own_events: 3*7=21 + 8=29)
        for pid in ["particle_epsilon", "particle_eta", "particle_zeta"]:
            assert ms[pid]["vector_sum"] == 29, (
                f"{pid} vector_sum: expected 29, got {ms[pid]['vector_sum']}"
            )

        # Colliders must have sum > 29 (they gain from collide self-increment + absorbed values)
        # Correct sums: alpha=51, beta=49, gamma=47, delta=51
        colliders_expected = {
            "particle_alpha": 51,
            "particle_beta": 49,
            "particle_gamma": 47,
            "particle_delta": 51,
        }
        for pid, expected_sum in colliders_expected.items():
            assert ms[pid]["vector_sum"] == expected_sum, (
                f"{pid} vector_sum: expected {expected_sum}, got {ms[pid]['vector_sum']}"
            )


# ═══════════════════════════════════════════════════════════════
# TIER 3: Trajectory classification (need Bugs 2+3 fixed)
# ═══════════════════════════════════════════════════════════════


class TestTier3TrajectoryClassification:
    """Tests that validate pair independence and priority ordering."""

    def test_priority_not_temporal(self):
        """Harvesting priority must NOT be based on temporal recency.

        Correct priority sorts by total momentum (vector sum).
        First particle must be one of the lowest-sum particles (epsilon/eta/zeta, sum=29).
        Last particle must be one of the highest-sum particles (alpha/delta, sum=51).
        """
        report = load_report()
        priority = report["harvesting_priority"]

        low_sum_particles = {"particle_epsilon", "particle_eta", "particle_zeta"}
        high_sum_particles = {"particle_alpha", "particle_delta"}

        assert priority[0] in low_sum_particles, (
            f"First in priority should be a low-sum particle (epsilon/eta/zeta), "
            f"got {priority[0]}"
        )
        assert priority[-1] in high_sum_particles, (
            f"Last in priority should be a high-sum particle (alpha/delta), "
            f"got {priority[-1]}"
        )

    def test_independent_pair_count(self):
        """Exactly 21 particle pairs must be classified as independent.

        With correct momentum vectors, no particle's vector dominates another's
        (each particle has its own component as the unique maximum). All 21
        pairs of 7 particles are trajectory-independent.
        """
        report = load_report()
        pair_data = report["pair_classification"]
        assert pair_data["independent_count"] == 21, (
            f"Independent pair count: expected 21, got {pair_data['independent_count']}. "
            f"Independence means neither vector dominates the other."
        )

    def test_classification_coverage(self):
        """All 21 pairs must be classified as independent with zero dependent pairs."""
        report = load_report()
        pair_data = report["pair_classification"]
        total = pair_data["independent_count"] + len(pair_data["dependent_pairs"])
        expected_total = 21  # C(7,2) = 21
        assert total == expected_total, (
            f"Total classified pairs: expected {expected_total}, got {total}"
        )
        # With correct vectors, all pairs must be independent (no dominance)
        assert len(pair_data["dependent_pairs"]) == 0, (
            f"Expected 0 dependent pairs, got {len(pair_data['dependent_pairs'])}. "
            f"No particle's vector should dominate another's."
        )


# ═══════════════════════════════════════════════════════════════
# TIER 4: Full consistency (need ALL bugs fixed)
# ═══════════════════════════════════════════════════════════════


class TestTier4Consistency:
    """Tests that validate end-to-end pipeline consistency."""

    def test_digest_fingerprint(self):
        """Report digest must match expected value for correct simulation.

        The 16-character hex digest validates that momentum vectors, pair
        classifications, and priority ordering are all correct simultaneously.
        """
        report = load_report()
        expected_digest = "771f0d20bdcc7ffb"
        actual_digest = report["validation"]["digest"]
        assert actual_digest == expected_digest, (
            f"Digest mismatch: expected {expected_digest}, got {actual_digest}. "
            f"This indicates one or more pipeline stages produce incorrect results."
        )

    def test_state_report_cross_validation(self):
        """State file vectors must match report momentum state exactly."""
        state = load_state()
        report = load_report()

        state_vectors = {}
        for record in state:
            if record["type"] == "particle_state":
                state_vectors[record["particle_id"]] = record["momentum_vector"]

        for pid in EXPECTED_PARTICLES:
            assert pid in state_vectors, f"{pid} missing from state file"
            assert pid in report["momentum_state"], f"{pid} missing from report"
            state_vec = state_vectors[pid]
            report_vec = report["momentum_state"][pid]["vector"]
            assert state_vec == report_vec, (
                f"{pid} vector mismatch between state and report: "
                f"state={state_vec}, report={report_vec}"
            )
