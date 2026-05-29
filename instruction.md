# Dataflow Widening Analysis — Debugging Task

## Overview

An abstract interpretation engine computes fixed points over a control flow graph (CFG) with 7 program points. Each point accumulates lattice height through dataflow operations (TRANSFER, WIDEN) and merges abstract states from predecessors via JOIN operations.

The pipeline performs these steps:
1. Parses the dataflow trace from `/app/runtime/data/abstract_trace.log`
2. Processes each operation through the lattice engine (`/app/runtime/lattice_engine.py`)
3. Computes convergence analysis (`/app/runtime/fixpoint_analyzer.py`)
4. Writes state to `/app/runtime/lattice_state.jsonl`
5. Writes the analysis report to `/app/runtime/analysis_report.jsonl`

## Observed Problem

The analysis runs without errors but produces incorrect results:

- The convergence report shows **0 converged pairs** when the analysis expects **14** out of 21 possible pairs
- The worklist ordering does not reflect total lattice height
- Entry's own lattice component reports **12** but integration of its operation history (4 TRANSFER + 2 WIDEN + 2 JOIN) suggests it should be **14**
- The report digest is `5b6a1228c3fbad78` instead of the expected `c07bf80123c73e95`

## Expected Behavior

When all bugs are fixed, the pipeline should:

1. **Lattice Engine (`/app/runtime/lattice_engine.py`)**: Each JOIN operation should merge ALL components of the predecessor state (including the point's own component via component-wise maximum), then increment the point's own component by 1. The own component must participate in the merge to absorb any predecessor knowledge about this point's lattice position.

2. **Convergence Analysis (`/app/runtime/fixpoint_analyzer.py`)**: Two program points have independently converged when their lattice vectors are *incomparable* in the partial order — meaning neither vector dominates the other component-wise. This indicates they reached their fixed points through independent computation paths.

3. **Worklist Priority (`/app/runtime/fixpoint_analyzer.py`)**: Points should be ordered by total lattice height (vector sum) to prioritize re-evaluation of points with the highest accumulated abstract values.

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

- `/app/runtime/data/abstract_trace.log` — the raw dataflow trace in tilde-arrow format
- `/app/runtime/cfg_parser.py` — parses trace into structured operation records
- `/app/runtime/run_analysis.py` — orchestrates the full analysis pipeline

## Files With Bugs

- `/app/runtime/lattice_engine.py` — lattice height vector computation during JOIN
- `/app/runtime/fixpoint_analyzer.py` — convergence predicate and worklist ordering
- `/app/runtime/analysis_report.py` — report writer (cascading from analyzer bugs)

## Output Schema

### `/app/runtime/lattice_state.jsonl`

One JSON object per line, one per program point (7 total):

```json
{"lattice_vector": [10, 10, 14, 9, 10, 10, 9], "point_id": "entry", "vector_sum": 72}
{"lattice_vector": [3, 3, 9, 3, 3, 13, 3], "point_id": "loop_head", "vector_sum": 37}
{"lattice_vector": [8, 12, 9, 9, 9, 8, 9], "point_id": "branch_t", "vector_sum": 64}
{"lattice_vector": [12, 3, 9, 3, 3, 8, 3], "point_id": "branch_f", "vector_sum": 41}
{"lattice_vector": [3, 3, 3, 3, 3, 3, 9], "point_id": "merge", "vector_sum": 27}
{"lattice_vector": [8, 8, 9, 9, 10, 8, 9], "point_id": "handler", "vector_sum": 61}
{"lattice_vector": [3, 3, 3, 9, 3, 3, 3], "point_id": "exit", "vector_sum": 27}
```

Vector component order corresponds to sorted point IDs: `[branch_f, branch_t, entry, exit, handler, loop_head, merge]`.

### `/app/runtime/analysis_report.jsonl`

```json
{"lattice_vector": [...], "point_id": "...", "type": "point_state", "vector_sum": N}
...
{"converged_count": 14, "converged_pairs": [[...], ...], "type": "convergence_analysis", "worklist_order": ["merge", "exit", "loop_head", "branch_f", "handler", "branch_t", "entry"]}
{"fingerprint": "c07bf80123c73e95", "type": "digest"}
```

## Expected Correct Values

| Metric | Expected Value |
|--------|---------------|
| Entry own lattice component | **14** |
| Total converged pairs | **14** (out of 21 possible) |
| Worklist order (last = highest priority) | **entry** (sum = 72) |
| Worklist order (first = lowest priority) | **merge** (sum = 27) |
| Report fingerprint digest | `c07bf80123c73e95` |
