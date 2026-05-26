# IR Optimizer Repair — Debugging Task

## Overview

A compiler intermediate representation (IR) optimization engine loads instruction streams from multiple modules (arithmetic operations, control flow, memory operations), orders them for processing, applies dead code elimination and constant folding passes, and produces optimization reports with per-module analysis metrics across configurable processing windows.

## System Environment

- **Language**: Python 3.11
- **Runtime**: `/app/runtime/` (source, config, data, output)
- **Global system-wide tooling**: `uv` and `pytest` are available

## Processing Stages

1. **Module Loading** — Reads CSV instruction files from each configured active module. Each module provides IR instructions with opcodes, operands, basic block assignments, and per-module sequence numbers. Module activation is managed by the `ModuleRegistry` class.

2. **Instruction Ordering** — Orders instructions for deterministic pass processing. Instructions are sorted by `(timestamp, module_id, seq)` to ensure consistent ordering when multiple instructions share the same timestamp across different modules.

3. **Pass Execution** — Runs optimization passes (constant folding and dead code elimination) over the ordered instruction stream. The engine uses pass-specific parameters from the `[optimizer.passes]` configuration section for pass depth and inline threshold settings. Instructions with unused results beyond the inline threshold are candidates for elimination.

4. **Window Metrics** — Computes per-module optimization metrics within analysis windows. The final metrics represent counts from the last processing window only, providing the most recent analysis snapshot.

5. **Report Generation** — Writes optimization results and analysis metrics to JSON files in the output directory.

## Problem

The engine runs without errors but produces incorrect optimization results:

- Some instruction modules appear to be missing from the analysis entirely
- The pass depth and inline threshold seem misconfigured, preventing effective dead code elimination
- Window metrics report inflated instruction counts that exceed single-window capacity
- Instruction ordering shows inconsistencies for instructions sharing the same timestamp

## Expected Correct Output

When all defects are fixed:

- All 55 instructions (20 arithmetic + 18 control_flow + 17 memory_ops) should be loaded
- Pass depth should be 2 with inline threshold of 10 (from pass-specific configuration)
- Dead code elimination should identify 6 eliminable instructions (unused results with seq > threshold)
- Window metrics should report per-module counts from the final window only: arithmetic total=4, control_flow total=2, memory_ops total=1
- Instructions at the same timestamp should be ordered deterministically by (timestamp, module_id, seq)

## Output Schema

### `/app/runtime/output/optimization_report.json`

| Field | Type | Description |
|-------|------|-------------|
| `instruction_order` | list | Ordered list of instruction metadata objects |
| `instruction_order[].instr_id` | string | Unique instruction identifier |
| `instruction_order[].module_id` | string | Source module name |
| `instruction_order[].opcode` | string | IR opcode |
| `instruction_order[].block_id` | string | Basic block identifier |
| `instruction_order[].timestamp` | integer | Instruction timestamp |
| `total_instructions` | integer | Total instructions loaded |
| `eliminated_count` | integer | Instructions eliminated by dead code pass |
| `folded_count` | integer | Instructions folded by constant propagation |
| `module_counts` | object | Number of instructions per module |
| `module_counts.arithmetic` | integer | Arithmetic instruction count |
| `module_counts.control_flow` | integer | Control flow instruction count |
| `module_counts.memory_ops` | integer | Memory operation count |
| `pass_depth` | integer | Number of optimization passes executed |

### `/app/runtime/output/analysis_metrics.json`

| Field | Type | Description |
|-------|------|-------------|
| `window_metrics` | object | Per-module metrics from final analysis window |
| `window_metrics.<module>.total` | integer | Instruction count in final window |
| `window_metrics.<module>.optimized` | integer | Optimized count in final window |
| `total_instructions` | integer | Total instructions processed |
| `modules_analyzed` | list | Sorted list of module names |
| `optimization_ratio` | float | Ratio of optimized to total instructions |

## Key Files

| File | Purpose |
|------|---------|
| `/app/runtime/config.ini` | Configuration with module list, optimizer parameters, and analysis settings |
| `/app/runtime/module_loader.py` | Loads IR instructions via ModuleRegistry; filters by active modules |
| `/app/runtime/pass_engine.py` | Orders instructions, runs optimization passes, computes window metrics |
| `/app/runtime/report_builder.py` | Constructs structured output from optimization results |
| `/app/runtime/run_optimizer.py` | Main entry point orchestrating the full process |
| `/app/runtime/data/arithmetic_ops.csv` | Arithmetic IR instructions (20 entries) |
| `/app/runtime/data/control_flow_ops.csv` | Control flow IR instructions (18 entries) |
| `/app/runtime/data/memory_ops.csv` | Memory operation IR instructions (17 entries) |

## Your Task

Identify and fix defects in the runtime source files under `/app/runtime/`. The data files are correct — the bugs are in the Python source code and its interaction with the configuration file. Focus on:

- How module names are resolved from the configuration in the registry
- Which configuration section provides optimization pass parameters (depth, threshold)
- How window metrics are aggregated across analysis windows
- How instructions with identical timestamps are ordered for processing
