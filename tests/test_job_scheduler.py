"""Test suite for the task scheduler engine.

Validates execution plan and resource utilization output by the engine.
Tests are structured in graduated difficulty from basic structural
checks to full correctness verification.
"""

import json
import os

OUTPUT_DIR = "/app/runtime/output"
SCHEDULE_PLAN_PATH = os.path.join(OUTPUT_DIR, "schedule_plan.json")
RESOURCE_REPORT_PATH = os.path.join(OUTPUT_DIR, "resource_report.json")


def _load_schedule_plan():
    """Load schedule plan JSON output."""
    with open(SCHEDULE_PLAN_PATH, "r") as f:
        return json.load(f)


def _load_resource_report():
    """Load resource report JSON output."""
    with open(RESOURCE_REPORT_PATH, "r") as f:
        return json.load(f)


# ============================================================
# EASY TESTS (pass even with buggy code)
# ============================================================


def test_output_files_exist():
    """Verify that the engine produces both expected output files."""
    assert os.path.exists(SCHEDULE_PLAN_PATH), (
        f"Missing output file: {SCHEDULE_PLAN_PATH}"
    )
    assert os.path.exists(RESOURCE_REPORT_PATH), (
        f"Missing output file: {RESOURCE_REPORT_PATH}"
    )


def test_schedule_plan_structure():
    """Verify the top-level structure of schedule_plan.json contains required keys."""
    data = _load_schedule_plan()
    assert "execution_plan" in data, "schedule_plan.json missing 'execution_plan' key"
    assert "total_jobs_scheduled" in data, (
        "schedule_plan.json missing 'total_jobs_scheduled' key"
    )
    assert "total_duration" in data, (
        "schedule_plan.json missing 'total_duration' key"
    )
    assert "critical_path_depth" in data, (
        "schedule_plan.json missing 'critical_path_depth' key"
    )
    assert "category_counts" in data, (
        "schedule_plan.json missing 'category_counts' key"
    )


def test_resource_report_structure():
    """Verify the top-level structure of resource_report.json contains required keys."""
    report = _load_resource_report()
    required_keys = ["epoch_resources", "total_jobs", "categories_scheduled"]
    for key in required_keys:
        assert key in report, f"resource_report.json missing '{key}' key"


def test_execution_plan_is_list():
    """Verify that execution plan entries have correct structure."""
    data = _load_schedule_plan()
    assert isinstance(data["execution_plan"], list), (
        "execution_plan should be a list"
    )
    assert len(data["execution_plan"]) > 30, (
        f"Expected more than 30 jobs in plan, got {len(data['execution_plan'])}"
    )
    first = data["execution_plan"][0]
    assert "job_id" in first, "execution_plan entries missing 'job_id'"
    assert "category_id" in first, "execution_plan entries missing 'category_id'"
    assert "priority" in first, "execution_plan entries missing 'priority'"


# ============================================================
# MEDIUM TESTS (require 1-2 bug fixes)
# ============================================================


def test_maintenance_category_scheduled():
    """Verify that maintenance category jobs are included in the schedule.

    The engine should schedule jobs from all configured active categories
    including maintenance. Check that maintenance jobs appear in the
    category counts.
    """
    data = _load_schedule_plan()
    counts = data["category_counts"]
    assert counts.get("maintenance", 0) >= 15, (
        f"Expected at least 15 maintenance jobs, got {counts.get('maintenance', 0)}. "
        f"Check category filtering in /app/runtime/job_loader.py — "
        f"verify active_categories parsing handles whitespace correctly."
    )


def test_correct_epoch_size_effect():
    """Verify that the scheduler uses the correct epoch size from config.

    The resource report should reflect processing with the parallel
    scheduling epoch size, not the generic scheduling epoch size. With
    correct epoch size of 10, resource values should differ from totals.
    """
    data = _load_schedule_plan()
    report = _load_resource_report()
    # With correct epoch_size=10, epoch_resources represent last epoch only
    # which should NOT equal total category durations
    compute_total = sum(
        j["duration"] for j in data["execution_plan"]
        if j["category_id"] == "compute"
    )
    compute_epoch = report["epoch_resources"].get("compute", 0)
    assert compute_epoch != compute_total, (
        f"Compute epoch_resources ({compute_epoch}) equals total compute duration "
        f"({compute_total}). Epoch resources should reflect the final epoch only. "
        f"Check which config section provides epoch_size in "
        f"/app/runtime/scheduler_engine.py — use [scheduling.parallel] section."
    )


def test_epoch_resource_values():
    """Verify that epoch resources reflect per-epoch utilization correctly.

    The resources should report the category durations from the final
    processing epoch only, not accumulated totals across all epochs.
    """
    report = _load_resource_report()
    resources = report["epoch_resources"]
    assert "maintenance" in resources, (
        f"epoch_resources missing 'maintenance' category — "
        f"maintenance jobs must be scheduled first (check category loading)."
    )
    assert resources["maintenance"] == 135, (
        f"Expected epoch_resources['maintenance']=135, got {resources['maintenance']}. "
        f"Resources should reflect the final epoch's durations, not accumulated totals. "
        f"Check /app/runtime/scheduler_engine.py compute_epoch_resources method."
    )
    assert resources["compute"] == 905, (
        f"Expected epoch_resources['compute']=905, got {resources['compute']}."
    )
    assert resources["io"] == 355, (
        f"Expected epoch_resources['io']=355, got {resources['io']}."
    )


# ============================================================
# HARD TESTS (require 3-4 bug fixes together)
# ============================================================


def test_priority_tiebreaker_ordering():
    """Verify correct ordering of jobs with equal priority.

    Jobs with the same priority must be ordered by (category_id, seq) for
    deterministic scheduling. At priority 85, CMP005 (compute, seq=5)
    should come before IOJ015 (io, seq=3) because 'compute' < 'io'
    alphabetically. Check the sort key in /app/runtime/scheduler_engine.py
    resolve_execution_order method.
    """
    data = _load_schedule_plan()
    plan = data["execution_plan"]

    # Find CMP005 and IOJ015 positions (both priority 85)
    cmp005_pos = None
    ioj015_pos = None
    for entry in plan:
        if entry["job_id"] == "CMP005":
            cmp005_pos = entry["position"]
        elif entry["job_id"] == "IOJ015":
            ioj015_pos = entry["position"]

    assert cmp005_pos is not None, (
        "CMP005 not found in execution plan."
    )
    assert ioj015_pos is not None, (
        "IOJ015 not found in execution plan."
    )
    assert cmp005_pos < ioj015_pos, (
        f"CMP005 (position {cmp005_pos}) should come before IOJ015 "
        f"(position {ioj015_pos}) because at equal priority, category_id "
        f"provides tiebreaking ('compute' < 'io'). Check sort key includes "
        f"category_id in /app/runtime/scheduler_engine.py — sort should be "
        f"(-priority, category_id, seq)."
    )


def test_total_jobs_scheduled():
    """Verify the correct total number of jobs are scheduled.

    All three categories (compute: 20, io: 18, maintenance: 17) should
    be loaded and scheduled, giving a total of 55 jobs.
    """
    data = _load_schedule_plan()
    assert data["total_jobs_scheduled"] == 55, (
        f"Expected 55 total jobs scheduled (20+18+17), "
        f"got {data['total_jobs_scheduled']}. "
        f"Check that all active categories are loaded correctly."
    )
    report = _load_resource_report()
    assert report["total_jobs"] == 55, (
        f"Expected total_jobs=55, got {report['total_jobs']}."
    )
    assert "maintenance" in report["categories_scheduled"], (
        "categories_scheduled should include 'maintenance'."
    )


def test_full_duration_accuracy():
    """Verify total duration is computed correctly with all categories included.

    With all 55 jobs scheduled, total duration should reflect compute,
    io, and maintenance jobs combined.
    """
    data = _load_schedule_plan()
    assert data["total_duration"] == 3585, (
        f"Expected total_duration=3585, got {data['total_duration']}. "
        f"Duration must include maintenance jobs."
    )
    counts = data["category_counts"]
    assert counts.get("compute") == 20, (
        f"Expected 20 compute jobs, got {counts.get('compute')}."
    )
    assert counts.get("io") == 18, (
        f"Expected 18 io jobs, got {counts.get('io')}."
    )
    assert counts.get("maintenance") == 17, (
        f"Expected 17 maintenance jobs, got {counts.get('maintenance')}."
    )
