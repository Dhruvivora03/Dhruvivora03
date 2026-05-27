# Bytecode Optimizer Repair — Debugging Task

## Overview

A batch bytecode compiler processes arithmetic expression programs, compiling them to stack-based bytecode instructions and applying configurable optimization passes. The system reads source files, parses them into ASTs, emits bytecode, runs optimization passes (constant folding, dead store elimination, peephole), and outputs compilation results with aggregate statistics.

## System Environment

- **Language**: Python 3.11
- **Runtime**: `/app/runtime/` (source, config, data, output)
- **Global system-wide tooling**: `uv` and `pytest` are available

## Processing Stages

1. **Source Loading** — Reads source program files from the configured data directory based on the source file list in the compiler configuration.

2. **Parsing** — Parses each source file into an AST representation. Supports variable assignments, print statements, and arithmetic expressions with standard operator precedence.

3. **Bytecode Emission** — Walks the AST and emits stack-based bytecode instructions. Variable references are resolved against the symbol table built during parsing.

4. **Optimization** — Applies registered optimization passes to the raw bytecode. Passes include constant folding (collapses compile-time constant expressions), dead store elimination (removes unused variable stores), and peephole optimization (simplifies identity operations like x+0, x*1). The optimization level from the pass configuration determines which passes are active.

5. **Statistics Collection** — Collects per-file and aggregate compilation statistics including instruction counts and per-pass elimination counts. Each file's statistics should reflect only that file's optimizations independently.

6. **Output Generation** — Writes compilation results and statistics as JSON files.

## Problem

The compiler runs without errors but produces incorrect output:

- One source file is not being compiled despite being configured
- Constant folding produces wrong results for subtraction and division expressions
- The peephole optimization pass is not running despite being configured
- Some variable references emit incorrect bytecode, producing wrong computed values

## Expected Correct Output

When all defects are fixed:

- All 3 source files (arithmetic.src, complex.src, variables.src) should be compiled
- Constant folding should produce correct values: `10+5=15`, `100-37=63`, `50-8=42`, `48/6=8.0`
- The peephole pass should be active (optimization level 3 enables all passes)
- All variable references should resolve correctly through the symbol table
- Per-file pass statistics should be independent (not accumulated across files)
- Total instructions eliminated across all files: 24

## Output Schema

### `/app/runtime/output/compilation_results.json`

| Field | Type | Description |
|-------|------|-------------|
| `compilation_units` | list | List of compiled file results |
| `compilation_units[].filename` | string | Source filename |
| `compilation_units[].raw_instructions` | list | Unoptimized bytecode instruction list |
| `compilation_units[].optimized_instructions` | list | Optimized bytecode instruction list |
| `compilation_units[].symbol_table` | object | Variables defined in the file |
| `compilation_units[].raw_count` | integer | Number of raw instructions |
| `compilation_units[].optimized_count` | integer | Number of optimized instructions |

### `/app/runtime/output/compiler_stats.json`

| Field | Type | Description |
|-------|------|-------------|
| `files_compiled` | integer | Number of source files compiled |
| `file_stats` | list | Per-file compilation statistics |
| `file_stats[].filename` | string | Source filename |
| `file_stats[].raw_instructions` | integer | Raw instruction count |
| `file_stats[].optimized_instructions` | integer | Optimized instruction count |
| `file_stats[].eliminated` | integer | Instructions eliminated for this file |
| `file_stats[].pass_stats` | object | Per-pass elimination counts for this file |
| `total_instructions_eliminated` | integer | Sum of eliminations across all files |
| `pass_eliminations` | object | Per-pass elimination counts (last file only) |
| `optimization_level` | integer | Active optimization level |
| `active_passes` | list | Names of active optimization passes |

## Key Files

| File | Purpose |
|------|---------|
| `/app/runtime/config.ini` | Compiler and optimizer configuration |
| `/app/runtime/parser.py` | Source code parser producing AST with symbol table |
| `/app/runtime/emitter.py` | AST-to-bytecode emission with variable resolution |
| `/app/runtime/optimizer.py` | Optimization passes (constant fold, dead store, peephole) |
| `/app/runtime/compiler.py` | Batch compilation orchestration and statistics |
| `/app/runtime/run_compiler.py` | Entry point |
| `/app/runtime/data/arithmetic.src` | Arithmetic test program |
| `/app/runtime/data/complex.src` | Complex expressions with identity operations |
| `/app/runtime/data/variables.src` | Variable assignment and reference program |

## Your Task

Identify and fix defects in the runtime source files under `/app/runtime/`. The source program files and entry point are correct — the bugs are in the compiler internals and their interaction with the configuration. Focus on:

- How source file names are parsed from configuration
- How the constant folding pass handles operand ordering for stack-based operations
- How optimization pass statistics are tracked across multiple compilation units
- How variable names flow through parsing, symbol table construction, and bytecode emission
