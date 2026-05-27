"""Test suite for the deadline task scheduling engine.

Validates execution plan and queue statistics output by the engine.
Tests are structured in graduated difficulty from basic structural
checks to full correctness verification.
"""

import json
import os

OUTPUT_DIR = "/app/runtime/output"
EXECUTION_PLAN_PATH = os.path.join(OUTPUT_DIR, "execution_plan.json")
QUEUE_STATS_PATH = os.path.join(OUTPUT_DIR, "queue_stats.json")


def _load_execution_plan():
    """Load execution plan JSON output."""
    with open(EXECUTION_PLAN_PATH, "r") as f:
        return json.load(f)


def _load_queue_stats():
    """Load queue statistics JSON output."""
    with open(QUEUE_STATS_PATH, "r") as f:
        return json.load(f)


# ============================================================
# EASY TESTS (pass even with buggy code)
# ============================================================


def test_output_files_exist():
    """Verify that the engine produces both expected output files."""
    assert os.path.exists(EXECUTION_PLAN_PATH), (
        f"Missing output file: {EXECUTION_PLAN_PATH}"
    )
    assert os.path.exists(QUEUE_STATS_PATH), (
        f"Missing output file: {QUEUE_STATS_PATH}"
    )


def test_execution_plan_structure():
    """Verify the top-level structure of execution_plan.json contains required keys."""
    data = _load_execution_plan()
    assert "execution_plan" in data, "execution_plan.json missing 'execution_plan' key"
    assert "top_priority_jobs" in data, (
        "execution_plan.json missing 'top_priority_jobs' key"
    )
    assert "total_jobs_loaded" in data, (
        "execution_plan.json missing 'total_jobs_loaded' key"
    )


def test_queue_stats_structure():
    """Verify the top-level structure of queue_stats.json contains required keys."""
    stats = _load_queue_stats()
    required_keys = [
        "queue_statistics", "resolution_summary",
        "wave_processing_stats", "execution_config",
    ]
    for key in required_keys:
        assert key in stats, f"queue_stats.json missing '{key}' key"


def test_execution_plan_is_list():
    """Verify that execution plan entries are returned as a list."""
    data = _load_execution_plan()
    assert isinstance(data["execution_plan"], list), (
        "execution_plan should be a list"
    )
    assert len(data["execution_plan"]) >= 30, (
        f"Expected at least 30 plan entries, got {len(data['execution_plan'])}"
    )


# ============================================================
# MEDIUM TESTS (require 1-2 bug fixes)
# ============================================================


def test_network_stream_jobs_loaded():
    """Verify that network stream jobs are included in the execution plan.

    The engine should load jobs from all configured active streams
    including the network stream. Check that network jobs appear in
    the execution plan with correct stream identification.
    """
    data = _load_execution_plan()
    network_jobs = [
        e for e in data["execution_plan"] if e["stream_id"] == "network"
    ]
    assert len(network_jobs) >= 10, (
        f"Expected at least 10 network jobs in execution plan, got {len(network_jobs)}. "
        f"Check stream filtering in /app/runtime/stream_loader.py — "
        f"verify active_streams parsing handles whitespace correctly."
    )


def test_correct_urgency_multiplier():
    """Verify that the priority queue uses the correct urgency multiplier.

    The scheduling engine should use the deadline-specific configuration
    for its urgency multiplier, resulting in proper priority scores.
    """
    stats = _load_queue_stats()
    assert stats["queue_statistics"]["urgency_multiplier"] == 2.5, (
        f"Expected urgency_multiplier=2.5, got "
        f"{stats['queue_statistics']['urgency_multiplier']}. "
        f"Check which config section is used in /app/runtime/priority_queue.py — "
        f"the deadline-specific parameters are in [scheduling.deadline]."
    )


def test_wave_processing_statistics():
    """Verify that wave processing statistics reflect per-wave counts correctly.

    The wave statistics should report the job counts from the final
    processing wave, not accumulated totals across all waves.
    """
    stats = _load_queue_stats()
    wave_stats = stats["wave_processing_stats"]
    assert "network" in wave_stats, (
        f"wave_processing_stats missing 'network' stream — "
        f"network jobs must be loaded first (check stream loading)."
    )
    assert wave_stats["compute"] == 1, (
        f"Expected wave_processing_stats['compute']=1, got {wave_stats['compute']}. "
        f"Statistics should reflect the final wave's counts, not accumulated totals. "
        f"Check /app/runtime/dependency_resolver.py resolve method."
    )
    assert wave_stats["io"] == 2, (
        f"Expected wave_processing_stats['io']=2, got {wave_stats['io']}."
    )
    assert wave_stats["network"] == 1, (
        f"Expected wave_processing_stats['network']=1, got {wave_stats['network']}."
    )


# ============================================================
# HARD TESTS (require 3-4 bug fixes together)
# ============================================================


def test_execution_ordering_tiebreaker():
    """Verify correct ordering of jobs with equal priority scores.

    Execution ordering must be sorted by (-priority_score, stream_id,
    seq_number) to produce deterministic ordering when multiple jobs
    share the same priority score. Check the sort key in
    /app/runtime/priority_queue.py build_queue method.
    """
    data = _load_execution_plan()
    plan = data["execution_plan"]

    # Find the tied pair: C016 and N003 both have score 5.175
    c016_pos = None
    n003_pos = None
    for i, entry in enumerate(plan):
        if entry["id"] == "C016":
            c016_pos = i
        elif entry["id"] == "N003":
            n003_pos = i

    assert c016_pos is not None, (
        "C016 not found in execution plan — check that compute stream is loaded."
    )
    assert n003_pos is not None, (
        "N003 not found in execution plan — network stream must be loaded. "
        "Check /app/runtime/stream_loader.py active_streams parsing."
    )

    assert c016_pos < n003_pos, (
        f"C016 (compute, seq=16) should come before N003 (network, seq=3) "
        f"at equal priority score. Got C016 at position {c016_pos}, N003 at {n003_pos}. "
        f"Sort should be (-priority_score, stream_id, seq_number) — "
        f"check /app/runtime/priority_queue.py build_queue sort key."
    )


def test_total_jobs_loaded():
    """Verify the correct total number of jobs are loaded and enqueued.

    All three streams (compute: 20, io: 18, network: 17) should be loaded
    and enqueued, giving a total of 55 jobs.
    """
    data = _load_execution_plan()
    assert data["total_jobs_loaded"] == 55, (
        f"Expected 55 total jobs loaded (20+18+17), "
        f"got {data['total_jobs_loaded']}. "
        f"Check that all active streams are loaded correctly."
    )
    stats = _load_queue_stats()
    assert stats["queue_statistics"]["total_enqueued"] == 55, (
        f"Expected total_enqueued=55, got "
        f"{stats['queue_statistics']['total_enqueued']}."
    )


def test_full_plan_stream_distribution():
    """Verify all streams are represented with correct job counts in the plan.

    The execution plan should contain all 55 jobs distributed across
    the three streams with correct per-stream counts.
    """
    data = _load_execution_plan()
    plan = data["execution_plan"]
    assert len(plan) == 55, (
        f"Execution plan should have 55 entries, got {len(plan)}."
    )
    stream_counts = {}
    for entry in plan:
        stream = entry["stream_id"]
        stream_counts[stream] = stream_counts.get(stream, 0) + 1
    assert stream_counts.get("compute", 0) == 20, (
        f"Expected 20 compute jobs, got {stream_counts.get('compute', 0)}."
    )
    assert stream_counts.get("io", 0) == 18, (
        f"Expected 18 io jobs, got {stream_counts.get('io', 0)}."
    )
    assert stream_counts.get("network", 0) == 17, (
        f"Expected 17 network jobs, got {stream_counts.get('network', 0)}."
    )
