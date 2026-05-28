# Lattice Thermal Diffusion Simulation -- Debugging Task

## Overview

A lattice-based thermal diffusion simulation processes energy propagation events across 7 lattice nodes. The simulation reads a trace log of thermal events (DIFFUSE, CONVECT, EQUILIBRATE), computes per-node energy vectors, classifies thermal independence between node pairs, and generates a scheduling priority for parallel simulation dispatch.

The system is producing incorrect results in multiple areas: energy accumulation, independence classification, and scheduling priority.

## Expected Behavior

- Each node maintains a 7-element energy vector tracking accumulated energy from all nodes' perspectives
- DIFFUSE events add 1 to the node's own component
- CONVECT events add 2 to the node's own component
- EQUILIBRATE events synchronize thermal knowledge with a neighbor via component-wise maximum AND should record the equilibration as an active event
- Thermal independence between nodes should be determined by the correct mathematical criterion for the energy vector partial order
- Scheduling priority should reflect actual total accumulated energy

## Observed Symptoms

- Nodes that have processed EQUILIBRATE events show energy values that are consistently 1 unit lower than expected in their own component
- The number of independent pairs detected is lower than the true count
- The scheduling priority order does not match what total energy sums would produce -- specifically, nodes with high peak values in single dimensions are being ranked above nodes with higher total energy
- The final state digest does not match the verified correct value

## File Locations

All source files are at `/app/runtime/`:

- `/app/runtime/data/thermal_log.txt` -- input trace (CORRECT)
- `/app/runtime/log_parser.py` -- log parser (CORRECT)
- `/app/runtime/run_simulation.py` -- orchestrator (CORRECT)
- `/app/runtime/diffusion_engine.py` -- energy vector engine (HAS BUGS)
- `/app/runtime/lattice_analyzer.py` -- independence analysis (HAS BUGS)
- `/app/runtime/thermal_report.py` -- report generation (HAS BUGS -- cascading from analyzer)

## Output Schema

### thermal_state.jsonl (one JSON object per line, sorted by node_id)
```json
{
  "node_id": "<node_name>",
  "energy_vector": [<7 integers>],
  "vector_sum": <integer>,
  "independent_neighbors": [<list of node_ids>],
  "priority_rank": <integer 0-6>
}
```

### thermal_summary.json
```json
{
  "digest": "<16-char hex>",
  "total_nodes": 7,
  "independent_pair_count": <integer>,
  "independent_pairs": [[<node_a>, <node_b>], ...],
  "priority_order": [<nodes sorted by priority>],
  "total_energy": <integer>
}
```

## Constraints

- Only standard library modules are used
- Do not modify `log_parser.py`, `run_simulation.py`, or the input data
- The simulation must produce both output files with correct values
- All 14 tests must pass after repair
