"""
Tests for the warzone campaign state synchronization simulation.
Validates structural output, influence state correctness, operational
independence classification, and full simulation consistency.
"""

import json
import os
import sys
import hashlib
import base64

sys.path.insert(0, "/app/runtime")

STATE_FILE = "/app/runtime/campaign_state.jsonl"
REPORT_FILE = "/app/runtime/campaign_summary.json"

# Verification oracle: base64-encoded expected values from a verified
# correct simulation run. Decode at runtime for comparison.
_ORACLE_B64 = (
    "eyJkaWdlc3QiOiAiOGE0N2RhYzc3OWFhYjQ0NiIsICJrbm93bGVkZ2VfdHJh"
    "bnNmZXIiOiB7InpvbmVfZG9ja3MiOiB7ImluZGV4IjogMCwgIm1pbl92YWx1"
    "ZSI6IDl9fSwgIm5laWdoYm9yc19wZXJfem9uZSI6IDYsICJvd25faW5mbHVl"
    "bmNlcyI6IHsiem9uZV9jaXRhZGVsIjogMTgsICJ6b25lX2RvY2tzIjogMTQs"
    "ICJ6b25lX2ZvcmdlIjogMTEsICJ6b25lX2dyb3ZlIjogOSwgInpvbmVfa2Vl"
    "cCI6IDEwLCAiem9uZV9ydWlucyI6IDksICJ6b25lX3NwaXJlIjogMTF9LCAi"
    "cGFpcl9jb3VudCI6IDIxLCAicHJpb3JpdHlfbW9ub3RvbmljIjogdHJ1ZX0="
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
        assert os.path.isfile(STATE_FILE), "campaign_state.jsonl missing"
        assert os.path.isfile(REPORT_FILE), "campaign_summary.json missing"

    def test_zone_count(self):
        """Simulation must produce records for exactly 7 zones."""
        records = load_state()
        assert len(records) == 7

    def test_zone_ids(self):
        """All expected zone IDs must be present."""
        records = load_state()
        zone_ids = {r["zone_id"] for r in records}
        expected = {
            "zone_citadel", "zone_docks", "zone_forge", "zone_grove",
            "zone_keep", "zone_ruins", "zone_spire"
        }
        assert zone_ids == expected

    def test_vector_dimensions(self):
        """Each record must have a 7-element influence vector."""
        records = load_state()
        for rec in records:
            assert len(rec["influence_vector"]) == 7, (
                f"{rec['zone_id']} has {len(rec['influence_vector'])}-element vector"
            )

    def test_required_fields(self):
        """Each state record must contain all required fields."""
        records = load_state()
        required = {"zone_id", "influence_vector", "vector_sum",
                    "independent_zones", "priority_rank"}
        for rec in records:
            assert required.issubset(rec.keys()), (
                f"{rec['zone_id']} missing fields: {required - set(rec.keys())}"
            )

    def test_total_zone_count_in_report(self):
        """Report must contain correct total zone count."""
        report = load_report()
        assert report["total_zones"] == 7


# ============================================================
# TIER 2: Influence state tests (need Bug 1 fixed)
# ============================================================


class TestTier2InfluenceState:
    """Influence vector correctness -- requires proper RALLY handling."""

    def test_influence_after_rally(self):
        """Zones that processed RALLY must have correct own influence.

        The own-component influence must match the verified oracle value,
        which accounts for all event types including rally coordination.
        """
        oracle = _load_oracle()
        records = load_state()
        all_ids = sorted(r["zone_id"] for r in records)

        # Check zone_docks specifically (has RALLY, affected by bug)
        docks = next(r for r in records if r["zone_id"] == "zone_docks")
        own_idx = all_ids.index("zone_docks")
        expected = oracle["own_influences"]["zone_docks"]
        actual = docks["influence_vector"][own_idx]
        assert actual == expected, (
            f"zone_docks own influence expected {expected}, got {actual}. "
            f"RALLY events must always contribute to the zone's own component."
        )

    def test_rally_knowledge_transfer(self):
        """RALLY must transfer influence knowledge from allied zones.

        The component-wise max operation should absorb higher values from
        the ally's reported state into the local influence vector.
        """
        oracle = _load_oracle()
        records = load_state()
        docks = next(r for r in records if r["zone_id"] == "zone_docks")
        transfer = oracle["knowledge_transfer"]["zone_docks"]
        actual = docks["influence_vector"][transfer["index"]]
        assert actual >= transfer["min_value"], (
            f"zone_docks component[{transfer['index']}] expected >= "
            f"{transfer['min_value']}, got {actual}. "
            f"RALLY must absorb ally's higher values via max."
        )

    def test_influence_all_rally_zones(self):
        """All zones with RALLY must have correct own-component values.

        Verifies that every zone's own influence matches the oracle,
        confirming proper handling of rally contributions.
        """
        oracle = _load_oracle()
        records = load_state()
        all_ids = sorted(r["zone_id"] for r in records)

        for zone_id, expected_own in oracle["own_influences"].items():
            rec = next(r for r in records if r["zone_id"] == zone_id)
            own_idx = all_ids.index(zone_id)
            actual = rec["influence_vector"][own_idx]
            assert actual == expected_own, (
                f"{zone_id} own influence expected {expected_own}, got {actual}."
            )


# ============================================================
# TIER 3: Independence tests (need Bugs 2+3 fixed)
# ============================================================


class TestTier3Independence:
    """Operational independence classification -- requires correct predicate and priority."""

    def test_priority_ordering_by_sum(self):
        """Priority must be ordered by total influence sum (ascending).

        The priority_order in the report should be monotonically
        non-decreasing when mapped to vector_sum values.
        """
        records = load_state()
        report = load_report()
        priority = report["priority_order"]

        sums_in_order = []
        for zone in priority:
            rec = next(r for r in records if r["zone_id"] == zone)
            sums_in_order.append(rec["vector_sum"])

        for i in range(len(sums_in_order) - 1):
            assert sums_in_order[i] <= sums_in_order[i + 1], (
                f"Priority not sorted by sum: position {i} has sum "
                f"{sums_in_order[i]}, position {i+1} has sum "
                f"{sums_in_order[i+1]}. Must use total influence sum."
            )

    def test_independent_pair_count(self):
        """All zone pairs should be classified as operationally independent.

        With correct influence vectors, no vector dominates another in the
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
        """Every zone must be independent from all other zones.

        Each zone should list all other zones as independent neighbors.
        """
        oracle = _load_oracle()
        records = load_state()
        expected_neighbors = oracle["neighbors_per_zone"]
        for rec in records:
            actual = len(rec["independent_zones"])
            assert actual == expected_neighbors, (
                f"{rec['zone_id']} has {actual} independent zones, "
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
            len(r["independent_zones"]) for r in records
        )
        assert total_independent // 2 == report["independent_pair_count"], (
            f"Cross-validation failed: state has {total_independent // 2} pairs, "
            f"report claims {report['independent_pair_count']}"
        )

        # Verify priority order length
        assert len(report["priority_order"]) == 7

        # Verify total influence
        state_total = sum(r["vector_sum"] for r in records)
        assert report["total_influence"] == state_total
