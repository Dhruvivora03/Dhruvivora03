# Token Flow Repair

## Domain
Programming Languages / Compilers / Parsers

## Overview
You are given a dataflow liveness analysis system for a simple register-based bytecode language. The system reads bytecode instructions, computes live variable sets at each program point using backward dataflow analysis, builds an interference graph between variables, and produces a register allocation priority ordering.

The analysis pipeline consists of:
1. **Bytecode Parser** (`bytecode_parser.py`) — Parses instructions from a text file
2. **Liveness Engine** (`liveness_engine.py`) — Backward dataflow analysis computing LiveIn/LiveOut sets
3. **Interference Builder** (`interference_builder.py`) — Constructs interference graph from liveness data
4. **Allocation Scorer** (`allocation_scorer.py`) — Computes register allocation priority
5. **Analysis Output** (`analysis_output.py`) — Aggregates results and produces output files
6. **Run Analysis** (`run_analysis.py`) — Orchestrator entry point

## Input Format
The input is a plain text file (`data/bytecode_program.txt`) with one instruction per line:
```
LABEL: OPCODE DEST, SRC1, SRC2
```

Registers are named `r0`-`r9` where `r0` is the zero register (hardwired to 0).
The program contains 20 instructions across 3 basic blocks (BB0, BB1, BB2) with conditional and unconditional branches.

## Output Format
The system produces two output files:
- `liveness_results.jsonl` — One JSON record per instruction with `label`, `opcode`, `live_in`, and `live_out` fields
- `analysis_summary.json` — Contains interference graph, allocation priority, program stats, and a fingerprint digest

## Task
The analysis pipeline contains bugs that produce incorrect results. Your goal is to identify and fix the bugs so that:
- Liveness analysis computes correct LiveIn and LiveOut sets
- The interference graph correctly identifies which variables cannot share registers
- The allocation priority correctly orders variables for graph coloring

## Hints
- Review the dataflow equations carefully — the standard liveness equation is well-known
- Consider what "interference" means precisely in graph coloring register allocation
- Think about what metric makes sense for allocation priority in a constrained coloring problem

## Running
```bash
cd runtime/
python run_analysis.py
```

## Testing
```bash
cd runtime/
python run_analysis.py
cd ..
python -m pytest tests/test_dataflow.py -v
```
