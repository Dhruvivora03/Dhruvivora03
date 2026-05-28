"""
Dataflow Liveness Analysis Test Suite
======================================
14 tests across 4 tiers validating the correctness of:
- Bytecode parsing and output structure
- Liveness analysis results
- Interference graph and allocation priority
- Fingerprint digest and cross-validation

Oracle data is encoded to prevent trivial answer extraction.
"""

import os
import sys
import json
import base64
import hashlib
import pytest

# Paths
RUNTIME_DIR = "/app/runtime"
OUTPUT_DIR = RUNTIME_DIR
LIVENESS_FILE = os.path.join(OUTPUT_DIR, "liveness_results.jsonl")
SUMMARY_FILE = os.path.join(OUTPUT_DIR, "analysis_summary.json")
DATA_DIR = os.path.join(RUNTIME_DIR, "data")
PROGRAM_FILE = os.path.join(DATA_DIR, "bytecode_program.txt")

# Oracle blob (base64-encoded expected results)
ORACLE_BLOB = (
    "eyJsaXZlbmVzcyI6IHsiQkIwXzAiOiB7ImxpdmVfaW4iOiBbInI5Il0sICJsaXZlX291dCI6IFsi"
    "cjEiLCAicjkiXX0sICJCQjBfMSI6IHsibGl2ZV9pbiI6IFsicjEiLCAicjkiXSwgImxpdmVfb3V0"
    "IjogWyJyMSIsICJyMiIsICJyOSJdfSwgIkJCMF8yIjogeyJsaXZlX2luIjogWyJyMSIsICJyMiIs"
    "ICJyOSJdLCAibGl2ZV9vdXQiOiBbInIxIiwgInIyIiwgInIzIiwgInI5Il19LCAiQkIwXzMiOiB7"
    "ImxpdmVfaW4iOiBbInIxIiwgInIyIiwgInIzIiwgInI5Il0sICJsaXZlX291dCI6IFsicjEiLCAi"
    "cjIiLCAicjMiLCAicjQiLCAicjkiXX0sICJCQjBfNCI6IHsibGl2ZV9pbiI6IFsicjEiLCAicjIi"
    "LCAicjMiLCAicjQiLCAicjkiXSwgImxpdmVfb3V0IjogWyJyMSIsICJyMiIsICJyMyIsICJyNCIs"
    "ICJyNSIsICJyOSJdfSwgIkJCMF81IjogeyJsaXZlX2luIjogWyJyMSIsICJyMiIsICJyMyIsICJy"
    "NCIsICJyNSIsICJyOSJdLCAibGl2ZV9vdXQiOiBbInIxIiwgInIyIiwgInIzIiwgInI0IiwgInI1"
    "IiwgInI5Il19LCAiQkIwXzYiOiB7ImxpdmVfaW4iOiBbInIxIiwgInIyIiwgInIzIiwgInI0Iiwg"
    "InI1IiwgInI5Il0sICJsaXZlX291dCI6IFsicjEiLCAicjIiLCAicjMiLCAicjQiLCAicjUiLCAi"
    "cjkiXX0sICJCQjFfMCI6IHsibGl2ZV9pbiI6IFsicjEiLCAicjIiLCAicjMiLCAicjQiLCAicjUi"
    "XSwgImxpdmVfb3V0IjogWyJyMSIsICJyMiIsICJyMyIsICJyNCIsICJyNSIsICJyNiJdfSwgIkJC"
    "MV8xIjogeyJsaXZlX2luIjogWyJyMSIsICJyMiIsICJyMyIsICJyNCIsICJyNSIsICJyNiJdLCAi"
    "bGl2ZV9vdXQiOiBbInIxIiwgInIyIiwgInIzIiwgInI0IiwgInI1IiwgInI3Il19LCAiQkIxXzIi"
    "OiB7ImxpdmVfaW4iOiBbInIxIiwgInIyIiwgInIzIiwgInI0IiwgInI1IiwgInI3Il0sICJsaXZl"
    "X291dCI6IFsicjEiLCAicjIiLCAicjQiLCAicjUiLCAicjgiXX0sICJCQjFfMyI6IHsibGl2ZV9p"
    "biI6IFsicjEiLCAicjIiLCAicjQiLCAicjUiLCAicjgiXSwgImxpdmVfb3V0IjogWyJyMSIsICJy"
    "MiIsICJyNCIsICJyOSJdfSwgIkJCMV80IjogeyJsaXZlX2luIjogWyJyMSIsICJyMiIsICJyNCIs"
    "ICJyOSJdLCAibGl2ZV9vdXQiOiBbInIxIiwgInIyIiwgInI0IiwgInI5Il19LCAiQkIxXzUiOiB7"
    "ImxpdmVfaW4iOiBbInIxIiwgInIyIiwgInI0IiwgInI5Il0sICJsaXZlX291dCI6IFsicjEiLCAi"
    "cjIiLCAicjQiLCAicjUiLCAicjkiXX0sICJCQjFfNiI6IHsibGl2ZV9pbiI6IFsicjEiLCAicjIi"
    "LCAicjQiLCAicjUiLCAicjkiXSwgImxpdmVfb3V0IjogWyJyMSIsICJyMiIsICJyNCIsICJyNSIs"
    "ICJyOSJdfSwgIkJCMl8wIjogeyJsaXZlX2luIjogWyJyMSIsICJyMiIsICJyNCIsICJyNSIsICJy"
    "OSJdLCAibGl2ZV9vdXQiOiBbInIxIiwgInIyIiwgInI0IiwgInI2Il19LCAiQkIyXzEiOiB7Imxp"
    "dmVfaW4iOiBbInIxIiwgInIyIiwgInI0IiwgInI2Il0sICJsaXZlX291dCI6IFsicjIiLCAicjQi"
    "LCAicjciXX0sICJCQjJfMiI6IHsibGl2ZV9pbiI6IFsicjIiLCAicjQiLCAicjciXSwgImxpdmVf"
    "b3V0IjogWyJyNCIsICJyOCJdfSwgIkJCMl8zIjogeyJsaXZlX2luIjogWyJyNCIsICJyOCJdLCAi"
    "bGl2ZV9vdXQiOiBbInI5Il19LCAiQkIyXzQiOiB7ImxpdmVfaW4iOiBbInI5Il0sICJsaXZlX291"
    "dCI6IFtdfSwgIkJCMl81IjogeyJsaXZlX2luIjogW10sICJsaXZlX291dCI6IFtdfX0sICJpbnRl"
    "cmZlcmVuY2VfY291bnQiOiAzNCwgImludGVyZmVyZW5jZV9ncmFwaCI6IHsicjEiOiBbInIyIiwg"
    "InIzIiwgInI0IiwgInI1IiwgInI2IiwgInI3IiwgInI4IiwgInI5Il0sICJyMiI6IFsicjEiLCAi"
    "cjMiLCAicjQiLCAicjUiLCAicjYiLCAicjciLCAicjgiLCAicjkiXSwgInIzIjogWyJyMSIsICJy"
    "MiIsICJyNCIsICJyNSIsICJyNiIsICJyNyIsICJyOCIsICJyOSJdLCAicjQiOiBbInIxIiwgInIy"
    "IiwgInIzIiwgInI1IiwgInI2IiwgInI3IiwgInI4IiwgInI5Il0sICJyNSI6IFsicjEiLCAicjIi"
    "LCAicjMiLCAicjQiLCAicjYiLCAicjciLCAicjgiLCAicjkiXSwgInI2IjogWyJyMSIsICJyMiIs"
    "ICJyMyIsICJyNCIsICJyNSIsICJyNyIsICJyOSJdLCAicjciOiBbInIxIiwgInIyIiwgInIzIiwg"
    "InI0IiwgInI1IiwgInI2IiwgInI4Il0sICJyOCI6IFsicjEiLCAicjIiLCAicjMiLCAicjQiLCAi"
    "cjUiLCAicjciLCAicjkiXSwgInI5IjogWyJyMSIsICJyMiIsICJyMyIsICJyNCIsICJyNSIsICJy"
    "NiIsICJyOCJdfSwgInByaW9yaXR5X29yZGVyIjogWyJyMSIsICJyMiIsICJyMyIsICJyNCIsICJy"
    "NSIsICJyNiIsICJyNyIsICJyOCIsICJyOSJdLCAicHJpb3JpdHlfc2NvcmVzIjogeyJyMSI6IDgs"
    "ICJyMiI6IDgsICJyMyI6IDgsICJyNCI6IDgsICJyNSI6IDgsICJyNiI6IDcsICJyNyI6IDcsICJy"
    "OCI6IDcsICJyOSI6IDd9LCAiZmluZ2VycHJpbnQiOiAiMzc5NzljOTQ5Y2Q0NmJlYWQ5MzQxZDkw"
    "MjFhOTMyYTUifQ=="
)


def _decode_oracle():
    """Decode the oracle blob."""
    return json.loads(base64.b64decode(ORACLE_BLOB).decode())


def _load_liveness_results():
    """Load liveness results from the JSONL output file."""
    results = {}
    with open(LIVENESS_FILE, 'r') as f:
        for line in f:
            record = json.loads(line.strip())
            results[record["label"]] = record
    return results


def _load_summary():
    """Load the analysis summary JSON."""
    with open(SUMMARY_FILE, 'r') as f:
        return json.load(f)


# ============================================================
# TIER 1: Structural Tests (6 tests)
# ============================================================

class TestTier1Structural:
    """Tier 1: Verify output files exist and have correct structure."""

    def test_liveness_file_exists(self):
        """T1.1: liveness_results.jsonl must exist."""
        assert os.path.isfile(LIVENESS_FILE), \
            f"Output file not found: {LIVENESS_FILE}"

    def test_summary_file_exists(self):
        """T1.2: analysis_summary.json must exist."""
        assert os.path.isfile(SUMMARY_FILE), \
            f"Output file not found: {SUMMARY_FILE}"

    def test_liveness_record_count(self):
        """T1.3: liveness_results.jsonl must have exactly 20 records (one per instruction)."""
        results = _load_liveness_results()
        assert len(results) == 20, \
            f"Expected 20 liveness records, got {len(results)}"

    def test_liveness_record_format(self):
        """T1.4: Each liveness record must have label, opcode, live_in, live_out fields."""
        results = _load_liveness_results()
        required_fields = {"label", "opcode", "live_in", "live_out"}
        for label, record in results.items():
            assert required_fields.issubset(set(record.keys())), \
                f"Record {label} missing fields: {required_fields - set(record.keys())}"

    def test_register_names_valid(self):
        """T1.5: All register names in live sets must match r[0-9] pattern."""
        import re
        reg_pattern = re.compile(r'^r[0-9]$')
        results = _load_liveness_results()
        for label, record in results.items():
            for reg in record["live_in"] + record["live_out"]:
                assert reg_pattern.match(reg), \
                    f"Invalid register name '{reg}' at {label}"

    def test_summary_structure(self):
        """T1.6: analysis_summary.json must have required top-level keys."""
        summary = _load_summary()
        required_keys = {"program_stats", "interference_graph", "allocation_priority",
                        "allocation_order", "fingerprint"}
        assert required_keys.issubset(set(summary.keys())), \
            f"Summary missing keys: {required_keys - set(summary.keys())}"


# ============================================================
# TIER 2: Liveness Correctness (3 tests)
# ============================================================

class TestTier2Liveness:
    """Tier 2: Validate liveness analysis produces correct live sets."""

    def test_live_out_at_exit(self):
        """T2.1: LiveOut at program exit (BB2_5 RET) must be empty.
        No variables are live after the return instruction."""
        results = _load_liveness_results()
        actual_out = sorted(results["BB2_5"]["live_out"])
        actual_in = sorted(results["BB2_5"]["live_in"])
        assert actual_out == [], \
            f"LiveOut at BB2_5 (RET): expected [], got {actual_out}"
        assert actual_in == [], \
            f"LiveIn at BB2_5 (RET): expected [], got {actual_in}"

    def test_live_in_at_entry(self):
        """T2.2: LiveIn at program entry (BB0_0) must match oracle.
        At the first instruction, the only variable that could be live-in
        is one that is used before being defined later in the program flow."""
        oracle = _decode_oracle()
        results = _load_liveness_results()
        expected = sorted(oracle["liveness"]["BB0_0"]["live_in"])
        actual = sorted(results["BB0_0"]["live_in"])
        assert actual == expected, \
            f"LiveIn at BB0_0: expected {expected}, got {actual}"

    def test_live_sets_at_phi(self):
        """T2.3: LiveIn/LiveOut at PHI node (BB2_0) must correctly merge branch info."""
        oracle = _decode_oracle()
        results = _load_liveness_results()
        expected_in = sorted(oracle["liveness"]["BB2_0"]["live_in"])
        actual_in = sorted(results["BB2_0"]["live_in"])
        expected_out = sorted(oracle["liveness"]["BB2_0"]["live_out"])
        actual_out = sorted(results["BB2_0"]["live_out"])
        assert actual_in == expected_in, \
            f"LiveIn at BB2_0: expected {expected_in}, got {actual_in}"
        assert actual_out == expected_out, \
            f"LiveOut at BB2_0: expected {expected_out}, got {actual_out}"


# ============================================================
# TIER 3: Interference & Priority (3 tests)
# ============================================================

class TestTier3InterferencePriority:
    """Tier 3: Validate interference graph and allocation priority."""

    def test_interference_edge_count(self):
        """T3.1: Total interference edges must match oracle count."""
        oracle = _decode_oracle()
        summary = _load_summary()
        expected = oracle["interference_count"]
        actual = summary["program_stats"]["num_interference_edges"]
        assert actual == expected, \
            f"Interference edges: expected {expected}, got {actual}"

    def test_interference_graph_structure(self):
        """T3.2: Specific interference relationships must match oracle.
        Registers r6, r7, r8, r9 should have degree 7 (not 8)."""
        oracle = _decode_oracle()
        summary = _load_summary()
        for reg in ["r6", "r7", "r8", "r9"]:
            expected_neighbors = sorted(oracle["interference_graph"][reg])
            actual_neighbors = sorted(summary["interference_graph"].get(reg, []))
            assert actual_neighbors == expected_neighbors, \
                f"Interference for {reg}: expected {expected_neighbors}, got {actual_neighbors}"

    def test_allocation_priority_order(self):
        """T3.3: Allocation priority must be sorted by degree (most constrained first)."""
        oracle = _decode_oracle()
        summary = _load_summary()
        expected_order = oracle["priority_order"]
        actual_order = summary["allocation_order"]
        assert actual_order == expected_order, \
            f"Priority order: expected {expected_order}, got {actual_order}"


# ============================================================
# TIER 4: Digest & Cross-Validation (2 tests)
# ============================================================

class TestTier4Validation:
    """Tier 4: Fingerprint verification and cross-validation."""

    def test_fingerprint_matches(self):
        """T4.1: The analysis fingerprint must match the oracle digest."""
        oracle = _decode_oracle()
        summary = _load_summary()
        expected = oracle["fingerprint"]
        actual = summary["fingerprint"]
        assert actual == expected, \
            f"Fingerprint mismatch: expected {expected}, got {actual}"

    def test_cross_validation_consistency(self):
        """T4.2: Live sets, interference, and priority must be internally consistent.
        Recompute interference from liveness and verify it matches the summary."""
        results = _load_liveness_results()
        summary = _load_summary()

        # Collect all registers from liveness data
        all_regs = set()
        for record in results.values():
            all_regs.update(record["live_in"])
            all_regs.update(record["live_out"])

        # Recompute interference from liveness
        reg_list = sorted(all_regs)
        recomputed_edges = 0
        for i in range(len(reg_list)):
            for j in range(i + 1, len(reg_list)):
                ra, rb = reg_list[i], reg_list[j]
                interferes = False
                for record in results.values():
                    live_at_point = set(record["live_in"]) | set(record["live_out"])
                    if ra in live_at_point and rb in live_at_point:
                        interferes = True
                        break
                if interferes:
                    recomputed_edges += 1

        reported_edges = summary["program_stats"]["num_interference_edges"]
        assert recomputed_edges == reported_edges, \
            f"Cross-validation failed: recomputed {recomputed_edges} edges, " \
            f"summary reports {reported_edges}"
