"""Test suite for the IR optimization engine.

Validates optimization reports and analysis metrics produced by the engine.
Tests are structured in graduated difficulty from basic structural checks
to full correctness verification requiring all bugs to be fixed.
"""

import json
import os

OUTPUT_DIR = "/app/runtime/output"
OPT_REPORT_PATH = os.path.join(OUTPUT_DIR, "optimization_report.json")
ANALYSIS_PATH = os.path.join(OUTPUT_DIR, "analysis_metrics.json")


def _load_opt_report():
    """Load optimization report JSON output."""
    with open(OPT_REPORT_PATH, "r") as f:
        return json.load(f)


def _load_analysis():
    """Load analysis metrics JSON output."""
    with open(ANALYSIS_PATH, "r") as f:
        return json.load(f)


# ============================================================
# EASY TESTS (pass even with buggy code)
# ============================================================


def test_output_files_exist():
    """Verify that the engine produces both expected output files."""
    assert os.path.exists(OPT_REPORT_PATH), (
        f"Missing output file: {OPT_REPORT_PATH}"
    )
    assert os.path.exists(ANALYSIS_PATH), (
        f"Missing output file: {ANALYSIS_PATH}"
    )


def test_optimization_report_structure():
    """Verify the top-level structure of optimization_report.json."""
    data = _load_opt_report()
    required = [
        "instruction_order", "total_instructions", "eliminated_count",
        "folded_count", "module_counts", "pass_depth",
    ]
    for key in required:
        assert key in data, f"optimization_report.json missing '{key}' key"


def test_analysis_metrics_structure():
    """Verify the top-level structure of analysis_metrics.json."""
    data = _load_analysis()
    required = [
        "window_metrics", "total_instructions",
        "modules_analyzed", "optimization_ratio",
    ]
    for key in required:
        assert key in data, f"analysis_metrics.json missing '{key}' key"


def test_instruction_order_is_list():
    """Verify instruction_order is a non-empty list with correct structure."""
    data = _load_opt_report()
    assert isinstance(data["instruction_order"], list), (
        "instruction_order should be a list"
    )
    assert len(data["instruction_order"]) > 30, (
        f"Expected more than 30 instructions, got {len(data['instruction_order'])}"
    )
    first = data["instruction_order"][0]
    assert "instr_id" in first, "instruction_order entries missing 'instr_id'"
    assert "module_id" in first, "instruction_order entries missing 'module_id'"


# ============================================================
# MEDIUM TESTS (require 1-2 bug fixes)
# ============================================================


def test_memory_module_loaded():
    """Verify that memory_ops module instructions are included.

    The engine should load instructions from all configured active modules
    including memory_ops. Check that memory_ops appears in module counts.
    """
    data = _load_opt_report()
    counts = data["module_counts"]
    assert counts.get("memory_ops", 0) >= 15, (
        f"Expected at least 15 memory_ops instructions, got "
        f"{counts.get('memory_ops', 0)}. Check module filtering in "
        f"/app/runtime/module_loader.py — the ModuleRegistry._resolve_active_modules "
        f"method must handle whitespace in the comma-separated list."
    )


def test_correct_pass_depth():
    """Verify that the optimization engine uses the correct pass depth.

    The pass depth should come from the pass-specific configuration
    section, not the generic optimizer section. With correct depth,
    the dead code elimination should identify eliminable instructions.
    """
    data = _load_opt_report()
    assert data["pass_depth"] == 2, (
        f"Expected pass_depth=2, got {data['pass_depth']}. "
        f"Check which config section provides pass parameters in "
        f"/app/runtime/pass_engine.py — the pass-specific configuration "
        f"is in [optimizer.passes]."
    )


def test_window_metrics_values():
    """Verify that window metrics reflect per-window counts correctly.

    The metrics should report instruction counts from the final analysis
    window only, not accumulated totals across all windows.
    """
    data = _load_analysis()
    metrics = data["window_metrics"]
    assert "memory_ops" in metrics, (
        "window_metrics missing 'memory_ops' — memory module must be "
        "loaded first (check module loading)."
    )
    assert metrics["arithmetic"]["total"] == 4, (
        f"Expected window_metrics['arithmetic']['total']=4, got "
        f"{metrics['arithmetic']['total']}. Metrics should reflect the "
        f"final window only, not accumulated totals. Check "
        f"/app/runtime/pass_engine.py compute_window_metrics method."
    )
    assert metrics["control_flow"]["total"] == 2, (
        f"Expected window_metrics['control_flow']['total']=2, got "
        f"{metrics['control_flow']['total']}."
    )
    assert metrics["memory_ops"]["total"] == 1, (
        f"Expected window_metrics['memory_ops']['total']=1, got "
        f"{metrics['memory_ops']['total']}."
    )


# ============================================================
# HARD TESTS (require 3-4 bug fixes together)
# ============================================================


def test_instruction_ordering_at_same_timestamp():
    """Verify correct ordering of instructions sharing the same timestamp.

    Instructions at timestamp 1700001500 must be sorted by
    (timestamp, module_id, seq) to produce deterministic ordering.
    The correct order is: A015 (arithmetic), CF015 (control_flow),
    MEM015 (memory_ops). Check the sort key in
    /app/runtime/pass_engine.py order_instructions method.
    """
    data = _load_opt_report()
    order = data["instruction_order"]

    ts_instrs = [i for i in order if i["timestamp"] == 1700001500]
    assert len(ts_instrs) == 3, (
        f"Expected 3 instructions at timestamp 1700001500, got "
        f"{len(ts_instrs)}. All modules (including memory_ops) must be loaded."
    )

    assert ts_instrs[0]["instr_id"] == "A015", (
        f"First instruction at timestamp 1700001500 should be A015 "
        f"(arithmetic comes before control_flow alphabetically), "
        f"got {ts_instrs[0]['instr_id']}. Check sort key includes module_id "
        f"in /app/runtime/pass_engine.py — sort should be "
        f"(timestamp, module_id, seq)."
    )
    assert ts_instrs[1]["instr_id"] == "CF015", (
        f"Second instruction at timestamp 1700001500 should be CF015, "
        f"got {ts_instrs[1]['instr_id']}."
    )
    assert ts_instrs[2]["instr_id"] == "MEM015", (
        f"Third instruction at timestamp 1700001500 should be MEM015, "
        f"got {ts_instrs[2]['instr_id']}."
    )


def test_total_instructions_count():
    """Verify the correct total number of instructions are loaded.

    All three modules (arithmetic: 20, control_flow: 18, memory_ops: 17)
    should be loaded, giving a total of 55 instructions.
    """
    data = _load_opt_report()
    assert data["total_instructions"] == 55, (
        f"Expected 55 total instructions (20+18+17), "
        f"got {data['total_instructions']}. "
        f"Check that all active modules are loaded correctly."
    )
    analysis = _load_analysis()
    assert analysis["total_instructions"] == 55, (
        f"Expected total_instructions=55 in analysis, "
        f"got {analysis['total_instructions']}."
    )
    assert "memory_ops" in analysis["modules_analyzed"], (
        "modules_analyzed should include 'memory_ops'."
    )


def test_dead_code_elimination_results():
    """Verify that dead code elimination identifies correct instructions.

    With correct pass depth (2) and inline threshold (10), the optimizer
    should eliminate instructions that produce unused results and have
    seq > threshold. Expected: 6 eliminated instructions.
    """
    data = _load_opt_report()
    assert data["eliminated_count"] == 6, (
        f"Expected 6 eliminated instructions, got {data['eliminated_count']}. "
        f"Dead code elimination requires correct pass_depth and "
        f"inline_threshold from [optimizer.passes] config section, and "
        f"all modules must be loaded for proper use-def analysis."
    )
    # Optimization ratio should reflect eliminations
    analysis = _load_analysis()
    expected_ratio = round(6 / 55, 4)
    assert analysis["optimization_ratio"] == expected_ratio, (
        f"Expected optimization_ratio={expected_ratio}, "
        f"got {analysis['optimization_ratio']}."
    )
