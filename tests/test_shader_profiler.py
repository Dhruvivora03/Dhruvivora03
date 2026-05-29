"""
Test suite for GPU shader pipeline profiling system.

Validates profiling correctness across four tiers:
  Tier 1 (6 tests): Structural validation — output existence and format
  Tier 2 (3 tests): Cycle state values — per-shader vector correctness
  Tier 3 (3 tests): Pipeline classification — stage disjointness and priority
  Tier 4 (2 tests): Full consistency — digest and cross-validation
"""

import json
import os
import sys

sys.path.insert(0, "/app/runtime")

STATE_FILE = "/app/runtime/profiler_state.jsonl"
REPORT_FILE = "/app/runtime/pipeline_report.json"

EXPECTED_SHADERS = [
    "shader_compute",
    "shader_fragment",
    "shader_geometry",
    "shader_raytrace",
    "shader_tessctl",
    "shader_tesseval",
    "shader_vertex",
]

TOTAL_EVENTS = 45
EVENTS_PER_SHADER = {
    "shader_vertex": 9,
    "shader_fragment": 7,
    "shader_geometry": 5,
    "shader_tessctl": 6,
    "shader_tesseval": 6,
    "shader_compute": 6,
    "shader_raytrace": 6,
}


def load_state():
    """Load profiler state from JSONL file."""
    records = []
    with open(STATE_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_report():
    """Load pipeline report from JSON file."""
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

    def test_shader_count(self):
        """Profiler must track exactly 7 shader stages."""
        report = load_report()
        assert report["profiling_summary"]["shader_count"] == 7

    def test_shader_ids(self):
        """All expected shader IDs must be present in report."""
        report = load_report()
        shaders = sorted(report["profiling_summary"]["shaders"])
        assert shaders == EXPECTED_SHADERS

    def test_events_per_shader(self):
        """Event distribution must match trace file."""
        state = load_state()
        summary = None
        for record in state:
            if record["type"] == "event_summary":
                summary = record
                break
        assert summary is not None, "No event_summary record in state file"
        for sid, expected_count in EVENTS_PER_SHADER.items():
            actual = summary["per_shader"].get(sid, 0)
            assert actual == expected_count, (
                f"{sid}: expected {expected_count} events, got {actual}"
            )

    def test_required_fields(self):
        """Each shader state record must have required fields."""
        state = load_state()
        shader_records = [r for r in state if r["type"] == "shader_state"]
        for record in shader_records:
            assert "shader_id" in record
            assert "cycle_vector" in record
            assert "own_cycles" in record
            assert len(record["cycle_vector"]) == 7

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
# TIER 2: Cycle state values (need Bug 1 fixed)
# ═══════════════════════════════════════════════════════════════


class TestTier2CycleState:
    """Tests that validate cycle vector correctness after SYNC."""

    def test_cycles_after_sync(self):
        """Shader vertex's own cycles must be 15 after SYNC + subsequent events.

        Vertex has 9 events: SAMPLE(+1) + BURST(+2) + SAMPLE(+1) + SYNC(+1) +
        SAMPLE(+1) + BURST(+2) + SAMPLE(+1) + SAMPLE(+1) + BURST(+2) = BASE(3) + 12 = 15.
        If SYNC does not increment, own cycles is only 14.
        """
        state = load_state()
        for record in state:
            if record["type"] == "shader_state" and record["shader_id"] == "shader_vertex":
                assert record["own_cycles"] == 15, (
                    f"shader_vertex own_cycles: expected 15, got {record['own_cycles']}. "
                    f"SYNC events must increment the shader's own cycle count."
                )
                return
        assert False, "shader_vertex state record not found"

    def test_sync_knowledge_absorption(self):
        """Shader fragment must absorb vertex's cycle data during SYNC.

        Fragment syncs with peer_state showing vertex at 7. Fragment's vector
        at vertex's position (index 6) should be max(BASE, 7) = 7.
        """
        state = load_state()
        for record in state:
            if record["type"] == "shader_state" and record["shader_id"] == "shader_fragment":
                # Fragment's vector at vertex's index (index 6) should be 7
                assert record["cycle_vector"][6] == 7, (
                    f"shader_fragment vector[6]: expected 7 (absorbed from vertex via SYNC), "
                    f"got {record['cycle_vector'][6]}"
                )
                return
        assert False, "shader_fragment state record not found"

    def test_vector_sums_with_sync(self):
        """Shaders with SYNC events must have correct vector sums.

        Syncing shaders (vertex, fragment, geometry, tessctl) accumulate extra
        cycles from the sync event itself. Their vector sums must match expected
        correct values. Non-syncing shaders (compute, raytrace, tesseval) have sum=29.
        """
        report = load_report()
        cs = report["cycle_state"]

        # Non-syncing shaders have sum=29
        for sid in ["shader_compute", "shader_raytrace", "shader_tesseval"]:
            assert cs[sid]["vector_sum"] == 29, (
                f"{sid} vector_sum: expected 29, got {cs[sid]['vector_sum']}"
            )

        # Syncing shaders: correct sums include SYNC self-increment
        syncing_expected = {
            "shader_vertex": 51,
            "shader_fragment": 49,
            "shader_geometry": 47,
            "shader_tessctl": 51,
        }
        for sid, expected_sum in syncing_expected.items():
            assert cs[sid]["vector_sum"] == expected_sum, (
                f"{sid} vector_sum: expected {expected_sum}, got {cs[sid]['vector_sum']}"
            )


# ═══════════════════════════════════════════════════════════════
# TIER 3: Pipeline classification (need Bugs 2+3 fixed)
# ═══════════════════════════════════════════════════════════════


class TestTier3PipelineClassification:
    """Tests that validate stage disjointness and priority ordering."""

    def test_priority_not_temporal(self):
        """Scheduling priority must NOT be based on temporal recency.

        Correct priority sorts by total cycles (vector sum).
        First shader must be one of the lowest-sum stages (compute/raytrace/tesseval, sum=29).
        Last shader must be one of the highest-sum stages (vertex/tessctl, sum=51).
        """
        report = load_report()
        priority = report["scheduling_priority"]

        low_sum_shaders = {"shader_compute", "shader_raytrace", "shader_tesseval"}
        high_sum_shaders = {"shader_vertex", "shader_tessctl"}

        assert priority[0] in low_sum_shaders, (
            f"First in priority should be a low-sum shader (compute/raytrace/tesseval), "
            f"got {priority[0]}"
        )
        assert priority[-1] in high_sum_shaders, (
            f"Last in priority should be a high-sum shader (vertex/tessctl), "
            f"got {priority[-1]}"
        )

    def test_disjoint_pair_count(self):
        """Exactly 21 shader pairs must be classified as disjoint.

        With correct cycle vectors, no shader's vector dominates another's
        (each shader has its own component as the unique maximum). All 21
        pairs of 7 shaders have disjoint execution profiles.
        """
        report = load_report()
        pair_data = report["pair_classification"]
        assert pair_data["disjoint_count"] == 21, (
            f"Disjoint pair count: expected 21, got {pair_data['disjoint_count']}. "
            f"Disjointness means neither vector dominates the other."
        )

    def test_classification_no_coupled(self):
        """All 21 pairs must be disjoint with zero coupled pairs."""
        report = load_report()
        pair_data = report["pair_classification"]
        total = pair_data["disjoint_count"] + len(pair_data["coupled_pairs"])
        expected_total = 21  # C(7,2) = 21
        assert total == expected_total, (
            f"Total classified pairs: expected {expected_total}, got {total}"
        )
        assert len(pair_data["coupled_pairs"]) == 0, (
            f"Expected 0 coupled pairs, got {len(pair_data['coupled_pairs'])}. "
            f"No shader's vector should dominate another's."
        )


# ═══════════════════════════════════════════════════════════════
# TIER 4: Full consistency (need ALL bugs fixed)
# ═══════════════════════════════════════════════════════════════


class TestTier4Consistency:
    """Tests that validate end-to-end pipeline consistency."""

    def test_digest_fingerprint(self):
        """Report digest must match expected value for correct profiling.

        The 16-character hex digest validates that cycle vectors, pair
        classifications, and priority ordering are all correct simultaneously.
        """
        report = load_report()
        expected_digest = "58116a4dfeeaa55e"
        actual_digest = report["validation"]["digest"]
        assert actual_digest == expected_digest, (
            f"Digest mismatch: expected {expected_digest}, got {actual_digest}. "
            f"This indicates one or more pipeline stages produce incorrect results."
        )

    def test_state_report_cross_validation(self):
        """State file vectors must match report cycle state exactly."""
        state = load_state()
        report = load_report()

        state_vectors = {}
        for record in state:
            if record["type"] == "shader_state":
                state_vectors[record["shader_id"]] = record["cycle_vector"]

        for sid in EXPECTED_SHADERS:
            assert sid in state_vectors, f"{sid} missing from state file"
            assert sid in report["cycle_state"], f"{sid} missing from report"
            state_vec = state_vectors[sid]
            report_vec = report["cycle_state"][sid]["vector"]
            assert state_vec == report_vec, (
                f"{sid} vector mismatch between state and report: "
                f"state={state_vec}, report={report_vec}"
            )
