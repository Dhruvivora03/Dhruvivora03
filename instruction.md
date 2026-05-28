# Lattice Thermal Diffusion Simulation — Debugging Task

## Overview

A lattice-based thermal diffusion simulation processes energy propagation events across 7 lattice nodes. The simulation reads a trace log of thermal events (DIFFUSE, CONVECT, EQUILIBRATE), computes per-node energy vectors, classifies thermal independence between node pairs, and generates a scheduling priority for parallel simulation dispatch.

The system is producing incorrect results. Some energy values are wrong, thermal independence is never detected between any pair of nodes, and the scheduling priority appears to follow event timing rather than energy state.

## Expected Behavior

- Each node maintains a 7-element energy vector tracking accumulated energy from all nodes' perspectives
- DIFFUSE events add 1 to the node's own component
- CONVECT events add 2 to the node's own component
- EQUILIBRATE events synchronize knowledge with a neighbor (component-wise max)
- Thermal independence between nodes should be detected when appropriate
- Scheduling priority should reflect logical energy state

## Observed Symptoms

- `node_alpha` own energy component shows 17, expected 18
- `node_beta` own energy component shows 13, expected 14
- Independent pair count is 0, expected 21
- Priority order appears sorted by last event timestamp rather than energy accumulation
- Final digest is `9c23781252b6edea`, expected `2ebb5ffc5b5c4fd7`

## File Locations

All source files are at `/app/runtime/`:

- `/app/runtime/data/thermal_log.txt` — input trace (CORRECT)
- `/app/runtime/log_parser.py` — log parser (CORRECT)
- `/app/runtime/run_simulation.py` — orchestrator (CORRECT)
- `/app/runtime/diffusion_engine.py` — energy vector engine (HAS BUGS)
- `/app/runtime/lattice_analyzer.py` — independence analysis (HAS BUGS)
- `/app/runtime/thermal_report.py` — report generation (HAS BUGS — cascading from analyzer)

## Output Schema

### thermal_state.jsonl (one JSON object per line, sorted by node_id)
```json
{
  "node_id": "node_alpha",
  "energy_vector": [18, 3, 3, 3, 3, 3, 3],
  "vector_sum": 36,
  "independent_neighbors": ["node_beta", "node_delta", ...],
  "priority_rank": 5
}
```

### thermal_summary.json
```json
{
  "digest": "2ebb5ffc5b5c4fd7",
  "total_nodes": 7,
  "independent_pair_count": 21,
  "independent_pairs": [["node_alpha", "node_beta"], ...],
  "priority_order": ["node_epsilon", "node_eta", "node_delta", "node_zeta", "node_gamma", "node_alpha", "node_beta"],
  "total_energy": 228
}
```

## Constraints

- Only standard library modules are used
- Do not modify `log_parser.py`, `run_simulation.py`, or the input data
- The simulation must produce both output files with correct values
- All 14 tests must pass after repair
