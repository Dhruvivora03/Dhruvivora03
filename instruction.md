# Particle Field Energy Dissipation — Debugging Task

## Overview

A molecular dynamics simulation models 7 coupled particles in a conservative force field. Each particle accumulates energy through physical events (DRIFT, COLLIDE) and exchanges energy knowledge through COUPLE interactions with neighbors.

The simulation pipeline reads a trace log, processes events through the dissipation engine, analyzes the resulting energy field for decoupled particle pairs, and produces a stability report for safe shutdown sequencing.

## Observed Problem

The simulation runs without errors but produces incorrect results:

- The stability report shows **0 decoupled pairs** when the field analysis expects **19**
- The shutdown ordering appears to follow temporal event sequence rather than thermodynamic priority
- Alpha's own energy component reports **13** but integration of its event history (5 DRIFT + 2 COLLIDE + 2 COUPLE) suggests it should be **14**
- The report digest is `7c9b01d76666971e` instead of the expected `39e8b5fd76520962`

## File Layout

```
/app/runtime/
├── data/
│   └── particle_field.log    # Event trace (correct, do not modify)
├── trace_parser.py           # Log parser (correct, do not modify)
├── dissipation_engine.py     # Energy vector engine (contains bug)
├── field_analyzer.py         # Convergence analysis (contains bugs)
├── stability_report.py       # Report generation (affected by analyzer bugs)
└── simulate_field.py         # Orchestrator (correct, do not modify)
```

## Correct Files (do not modify)

- `/app/runtime/data/particle_field.log` — the raw event trace
- `/app/runtime/trace_parser.py` — parses the arrow-separated log format
- `/app/runtime/simulate_field.py` — orchestrates parsing, engine, and report generation

## Files With Bugs

- `/app/runtime/dissipation_engine.py` — energy vector computation
- `/app/runtime/field_analyzer.py` — field decoupling analysis and shutdown ordering
- `/app/runtime/stability_report.py` — report generation (imports from field_analyzer)

## Output Schema

### field_state.jsonl
```json
{"particle_id": "alpha", "energy_vector": [14, ...], "vector_sum": 72}
```

### stability_report.jsonl
```json
{"type": "particle_state", "particle_id": "alpha", "energy_vector": [...], "vector_sum": 72}
{"type": "field_analysis", "decoupled_pairs": [...], "decoupled_count": 19, "shutdown_order": [...]}
{"type": "digest", "fingerprint": "39e8b5fd76520962"}
```

## Expected Correct Values

- Alpha own energy component: **14**
- Total decoupled pairs: **19** (out of 21 possible)
- Shutdown order first: **epsilon** (lowest energy), last: **alpha** (highest energy)
- Report digest: `39e8b5fd76520962`
