"""Test suite for the merkle proof verification engine.

Validates verification reports and metrics output by the engine.
Tests are structured in graduated difficulty from basic structural
checks to full correctness verification.
"""

import json
import os

OUTPUT_DIR = "/app/runtime/output"
VERIFICATION_PATH = os.path.join(OUTPUT_DIR, "verification_report.json")
METRICS_PATH = os.path.join(OUTPUT_DIR, "metrics_report.json")


def _load_verification():
    """Load verification report JSON output."""
    with open(VERIFICATION_PATH, "r") as f:
        return json.load(f)


def _load_metrics():
    """Load metrics report JSON output."""
    with open(METRICS_PATH, "r") as f:
        return json.load(f)


# ============================================================
# EASY TESTS (pass even with buggy code)
# ============================================================


def test_output_files_exist():
    """Verify that the engine produces both expected output files."""
    assert os.path.exists(VERIFICATION_PATH), (
        f"Missing output file: {VERIFICATION_PATH}"
    )
    assert os.path.exists(METRICS_PATH), (
        f"Missing output file: {METRICS_PATH}"
    )


def test_verification_report_structure():
    """Verify the top-level structure of verification_report.json."""
    data = _load_verification()
    required = [
        "proof_order", "total_proofs", "verification_scores",
        "chain_counts", "rounds_executed", "chain_stats",
    ]
    for key in required:
        assert key in data, f"verification_report.json missing '{key}' key"


def test_metrics_report_structure():
    """Verify the top-level structure of metrics_report.json."""
    data = _load_metrics()
    required = [
        "window_metrics", "total_proofs",
        "chains_verified", "verification_coverage",
    ]
    for key in required:
        assert key in data, f"metrics_report.json missing '{key}' key"


def test_proof_order_is_list():
    """Verify proof_order is a non-empty list with correct structure."""
    data = _load_verification()
    assert isinstance(data["proof_order"], list), (
        "proof_order should be a list"
    )
    assert len(data["proof_order"]) > 30, (
        f"Expected more than 30 proofs, got {len(data['proof_order'])}"
    )
    first = data["proof_order"][0]
    assert "proof_id" in first, "proof_order entries missing 'proof_id'"
    assert "chain_id" in first, "proof_order entries missing 'chain_id'"


# ============================================================
# MEDIUM TESTS (require 1-2 bug fixes)
# ============================================================


def test_keccak_chain_loaded():
    """Verify that keccak256 chain proofs are included in verification.

    The engine should load proofs from all enabled chains including
    keccak256. Check that keccak256 appears in chain counts.
    """
    data = _load_verification()
    counts = data["chain_counts"]
    assert counts.get("keccak256", 0) >= 15, (
        f"Expected at least 15 keccak256 proofs, got "
        f"{counts.get('keccak256', 0)}. Check chain filtering in "
        f"/app/runtime/chain_registry.py — the _load_enabled_chains "
        f"method must handle whitespace in the comma-separated config value."
    )


def test_verification_coverage():
    """Verify that verification rounds produce correct coverage.

    With 3 verification rounds over all 55 proofs, the verification
    coverage should be approximately 0.2364 (13 of 55 proofs verified).
    Fewer rounds or missing chains will produce different coverage.
    """
    data = _load_metrics()
    assert data["verification_coverage"] == 0.2364, (
        f"Expected verification_coverage=0.2364, got "
        f"{data['verification_coverage']}. This requires correct "
        f"verification_rounds (3 rounds, not 2) AND all chains loaded. "
        f"Check the loop range in /app/runtime/verifier_engine.py "
        f"verify_proofs method — rounds should iterate range(rounds), "
        f"not range(rounds - 1)."
    )


def test_window_metrics_depth_transitions():
    """Verify that window metrics correctly count depth transitions.

    Depth transitions should be counted when the current proof depth
    is greater than OR EQUAL to the previous depth (not strictly
    greater). The final metrics should reflect the last window only.
    """
    data = _load_metrics()
    metrics = data["window_metrics"]
    assert "keccak256" in metrics, (
        "window_metrics missing 'keccak256' — keccak chain must be "
        "loaded first (check chain registry)."
    )
    # With correct >= comparison and assignment, last window sha256 has 3 transitions
    assert metrics["sha256"]["depth_transitions"] == 3, (
        f"Expected sha256 depth_transitions=3, got "
        f"{metrics['sha256']['depth_transitions']}. Depth transitions "
        f"count when current depth >= previous depth (not strictly >). "
        f"Also metrics should reflect last window only, not accumulated. "
        f"Check /app/runtime/verifier_engine.py compute_window_metrics."
    )


# ============================================================
# HARD TESTS (require 3-4 bug fixes together)
# ============================================================


def test_proof_ordering_at_same_timestamp():
    """Verify correct ordering of proofs sharing the same timestamp.

    Proofs at timestamp 1700001500 must be sorted by
    (timestamp, position, seq) to produce deterministic ordering.
    Position-based ordering ensures merkle tree node order is preserved.
    The correct order is: SP015 (pos=35), BP015 (pos=38), KP015 (pos=39).
    Check the sort key in /app/runtime/verifier_engine.py order_proofs method.
    """
    data = _load_verification()
    order = data["proof_order"]

    ts_proofs = [p for p in order if p["timestamp"] == 1700001500]
    assert len(ts_proofs) == 3, (
        f"Expected 3 proofs at timestamp 1700001500, got "
        f"{len(ts_proofs)}. All chains (including keccak256) must be loaded."
    )

    assert ts_proofs[0]["proof_id"] == "SP015", (
        f"First proof at timestamp 1700001500 should be SP015 "
        f"(position=35 is lowest), got {ts_proofs[0]['proof_id']}. "
        f"Sort key should use position for tiebreaking, not leaf_hash. "
        f"Check /app/runtime/verifier_engine.py order_proofs — "
        f"sort by (timestamp, position, seq) not (timestamp, leaf_hash, seq)."
    )
    assert ts_proofs[1]["proof_id"] == "BP015", (
        f"Second proof at timestamp 1700001500 should be BP015 "
        f"(position=38), got {ts_proofs[1]['proof_id']}."
    )
    assert ts_proofs[2]["proof_id"] == "KP015", (
        f"Third proof at timestamp 1700001500 should be KP015 "
        f"(position=39), got {ts_proofs[2]['proof_id']}."
    )


def test_total_proofs_count():
    """Verify the correct total number of proofs are loaded.

    All three chains (sha256: 20, blake2b: 18, keccak256: 17) should
    be loaded, giving a total of 55 proofs.
    """
    data = _load_verification()
    assert data["total_proofs"] == 55, (
        f"Expected 55 total proofs (20+18+17), "
        f"got {data['total_proofs']}. "
        f"Check that all enabled chains are loaded correctly."
    )
    metrics = _load_metrics()
    assert metrics["total_proofs"] == 55, (
        f"Expected total_proofs=55 in metrics, got {metrics['total_proofs']}."
    )
    assert "keccak256" in metrics["chains_verified"], (
        "chains_verified should include 'keccak256'."
    )


def test_full_verification_scores():
    """Verify that verification produces correct number of verified proofs.

    With 3 complete rounds over all 55 proofs, exactly 13 proofs should
    have a positive verification score. This requires all chains loaded
    AND correct number of rounds executed.
    """
    data = _load_verification()
    scores = data["verification_scores"]
    verified_count = sum(1 for s in scores.values() if s > 0)
    assert verified_count == 13, (
        f"Expected 13 proofs with positive verification score, "
        f"got {verified_count}. This requires: all 55 proofs loaded "
        f"(check chain registry), 3 verification rounds executed "
        f"(check loop range in verify_proofs), and correct ordering "
        f"(check sort key in order_proofs)."
    )
    assert len(scores) == 55, (
        f"Expected scores for all 55 proofs, got {len(scores)}."
    )
