"""Test suite for the bytecode compiler optimization system.

Validates compilation results and statistics output by the compiler.
Tests are structured in graduated difficulty from basic structural
checks to full correctness verification requiring all bugs to be fixed.
"""

import json
import os

OUTPUT_DIR = "/app/runtime/output"
RESULTS_PATH = os.path.join(OUTPUT_DIR, "compilation_results.json")
STATS_PATH = os.path.join(OUTPUT_DIR, "compiler_stats.json")


def _load_results():
    """Load compilation results JSON output."""
    with open(RESULTS_PATH, "r") as f:
        return json.load(f)


def _load_stats():
    """Load compiler statistics JSON output."""
    with open(STATS_PATH, "r") as f:
        return json.load(f)


def _get_unit(results, filename):
    """Get compilation unit by filename."""
    for unit in results["compilation_units"]:
        if unit["filename"] == filename:
            return unit
    return None


# ============================================================
# EASY TESTS (pass even with buggy code)
# ============================================================


def test_output_files_exist():
    """Verify that the compiler produces both expected output files."""
    assert os.path.exists(RESULTS_PATH), (
        f"Missing output file: {RESULTS_PATH}"
    )
    assert os.path.exists(STATS_PATH), (
        f"Missing output file: {STATS_PATH}"
    )


def test_compilation_results_structure():
    """Verify the top-level structure of compilation_results.json."""
    data = _load_results()
    assert "compilation_units" in data, (
        "compilation_results.json missing 'compilation_units' key"
    )
    assert isinstance(data["compilation_units"], list), (
        "compilation_units should be a list"
    )
    assert len(data["compilation_units"]) >= 2, (
        f"Expected at least 2 compilation units, got {len(data['compilation_units'])}"
    )


def test_stats_structure():
    """Verify the top-level structure of compiler_stats.json."""
    stats = _load_stats()
    required_keys = [
        "files_compiled", "file_stats", "total_instructions_eliminated",
        "pass_eliminations", "optimization_level", "active_passes",
    ]
    for key in required_keys:
        assert key in stats, f"compiler_stats.json missing '{key}' key"


def test_arithmetic_unit_exists():
    """Verify that arithmetic.src is compiled and produces bytecode."""
    data = _load_results()
    unit = _get_unit(data, "arithmetic.src")
    assert unit is not None, "arithmetic.src not found in compilation results"
    assert unit["raw_count"] == 26, (
        f"arithmetic.src should have 26 raw instructions, got {unit['raw_count']}"
    )


# ============================================================
# MEDIUM TESTS (require 1-2 bug fixes)
# ============================================================


def test_complex_src_compiled():
    """Verify that complex.src is included in compilation output.

    All three configured source files must be compiled. If complex.src
    is missing, check how source file names are parsed from the
    configuration in /app/runtime/compiler.py.
    """
    stats = _load_stats()
    assert stats["files_compiled"] == 3, (
        f"Expected 3 files compiled, got {stats['files_compiled']}. "
        f"One source file is not being loaded from the configuration."
    )
    data = _load_results()
    unit = _get_unit(data, "complex.src")
    assert unit is not None, (
        "complex.src missing from compilation results."
    )


def test_constant_fold_subtraction():
    """Verify that constant folding computes subtraction correctly.

    The expression '100 - 37' should fold to PUSH_CONST 63.
    """
    data = _load_results()
    unit = _get_unit(data, "arithmetic.src")
    assert unit is not None, "arithmetic.src not found"

    # Find the folded constant for 100-37 (should be 63)
    opt = unit["optimized_instructions"]
    folded_values = [
        i["operand"] for i in opt
        if i["opcode"] == "PUSH_CONST" and isinstance(i.get("operand"), (int, float))
        and i["operand"] not in (2,)  # exclude the literal 2 in 'a * 2'
    ]
    assert 63 in folded_values, (
        f"Expected PUSH_CONST 63 from folding '100 - 37', but found "
        f"constants: {folded_values}. The constant folding pass produces "
        f"incorrect results for non-commutative operations."
    )


def test_peephole_pass_active():
    """Verify that the peephole optimization pass is active.

    With optimization level 3, all passes including peephole should run.
    If peephole is missing, check which configuration section provides
    the optimization level parameter.
    """
    stats = _load_stats()
    assert "peephole" in stats["active_passes"], (
        f"Peephole pass not active. Active passes: {stats['active_passes']}. "
        f"Current optimization_level: {stats['optimization_level']}."
    )
    assert stats["optimization_level"] == 3, (
        f"Expected optimization_level=3, got {stats['optimization_level']}."
    )


# ============================================================
# HARD TESTS (require 3-4 bug fixes together)
# ============================================================


def test_variables_src_uses_load_var():
    """Verify that variable references emit LOAD_VAR, not PUSH_CONST 0.

    In variables.src, expressions like 'Y = X + 3' should emit
    LOAD_VAR for X, not PUSH_CONST 0. The variable resolution must
    correctly match references to their symbol table entries regardless
    of how variable names are normalized during parsing.
    """
    data = _load_results()
    unit = _get_unit(data, "variables.src")
    assert unit is not None, (
        "variables.src missing — fix source file loading first"
    )

    opt = unit["optimized_instructions"]
    load_var_ops = [i for i in opt if i["opcode"] == "LOAD_VAR"]
    assert len(load_var_ops) >= 5, (
        f"Expected at least 5 LOAD_VAR instructions in variables.src, "
        f"got {len(load_var_ops)}. Variable references are not resolving "
        f"correctly through the symbol table."
    )


def test_per_file_pass_stats_independent():
    """Verify that per-file pass statistics are tracked independently.

    Each file's pass_stats should reflect only that file's optimizations,
    not accumulated totals from previously compiled files. The optimizer
    state must be isolated between compilation units.
    """
    stats = _load_stats()
    assert stats["files_compiled"] == 3, (
        "Need all 3 files compiled to validate pass stats"
    )

    # arithmetic.src should have constant_fold=6 independently
    arith_stats = None
    for fs in stats["file_stats"]:
        if fs["filename"] == "arithmetic.src":
            arith_stats = fs
            break
    assert arith_stats is not None, "arithmetic.src not in file_stats"

    arith_cf = arith_stats["pass_stats"].get("constant_fold", 0)
    assert arith_cf == 6, (
        f"arithmetic.src pass_stats['constant_fold'] should be 6, "
        f"got {arith_cf}. Per-file pass statistics are not independent."
    )


def test_total_instructions_eliminated():
    """Verify the correct total number of instructions eliminated.

    With all optimizations working correctly (constant folding with
    proper operand order, peephole active, all files compiled, correct
    variable resolution), the total eliminations should be 24.
    """
    stats = _load_stats()
    assert stats["total_instructions_eliminated"] == 24, (
        f"Expected 24 total instructions eliminated, "
        f"got {stats['total_instructions_eliminated']}. "
        f"This requires all source files compiled, correct constant "
        f"folding, active peephole pass, proper variable resolution, "
        f"and independent per-file statistics."
    )
