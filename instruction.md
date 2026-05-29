# Abstract Interpretation Fixed-Point Analysis — Debugging Task

## Overview

An abstract interpretation engine computes fixed points over a control flow graph with 7 program points. Each point accumulates lattice height through dataflow operations (TRANSFER, WIDEN) and merges abstract states from predecessors via JOIN operations.

The pipeline reads a dataflow trace, processes operations through the lattice engine, analyzes convergence of program point pairs, and produces an analysis report for worklist scheduling.

## Observed Problem

The analysis runs without errors but produces incorrect results:

- The convergence report shows **0 converged pairs** when analysis expects **14**
- The worklist ordering does not reflect total lattice height
- Entry's own lattice component reports **13** but should be **14**
- The report digest is `02b58225c80b7c02` instead of the expected `c07bf80123c73e95`

## File Layout

```
/app/runtime/
├── data/
│   └── abstract_trace.log     # Dataflow trace (correct, do not modify)
├── cfg_parser.py              # Trace parser (correct, do not modify)
├── lattice_engine.py          # Lattice state engine (contains bug)
├── fixpoint_analyzer.py       # Convergence analysis (contains bugs)
├── analysis_report.py         # Report generation (affected by analyzer bugs)
└── run_analysis.py            # Orchestrator (correct, do not modify)
```

## Correct Files (do not modify)

- `/app/runtime/data/abstract_trace.log`
- `/app/runtime/cfg_parser.py`
- `/app/runtime/run_analysis.py`

## Files With Bugs

- `/app/runtime/lattice_engine.py`
- `/app/runtime/fixpoint_analyzer.py`
- `/app/runtime/analysis_report.py`

## Expected Correct Values

- Entry own lattice component: **14**
- Total converged pairs: **14** (out of 21 possible)
- Worklist order last: **entry** (highest lattice sum of 72)
- Report digest: `c07bf80123c73e95`
