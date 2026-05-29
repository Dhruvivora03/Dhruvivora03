# Particle Collision Simulation — Debugging Task

## Overview

A particle collision simulation models 7 particles in an isolated chamber, tracking their momentum accumulation through drift, thrust, and collision events. The simulation reads a trace log, builds per-particle momentum vectors, classifies trajectory relationships between particles, and generates a report with priority ordering for energy harvesting probes.

The simulation is producing incorrect results. Several output values do not match expected values from validated reference runs.

## Observed Symptoms

1. **Momentum values too low**: Particle alpha should have own momentum of **15** after all events, but the simulation reports **14**. Similarly, particle beta reports 11 instead of expected 12, gamma reports 8 instead of 9, and delta reports 10 instead of 11.

2. **No independent pairs detected**: The trajectory report shows 0 independent particle pairs, but the expected count is **21** (all pairs should be independent given the collision chamber geometry).

3. **Wrong priority ordering**: The harvesting priority list starts with `particle_gamma` and ends with `particle_beta`, but correct ordering should start with a low-momentum particle (`particle_epsilon`) and end with a high-momentum particle (`particle_delta`).

4. **Digest mismatch**: Expected digest is `771f0d20bdcc7ffb`, simulation produces `7f4ebfaa6240c20a`.

## File Layout

All runtime files are located at `/app/runtime/`:

```
/app/runtime/
├── data/
│   └── collision_trace.log    — Event trace (input data)
├── trace_parser.py            — Parses trace log into events
├── momentum_tracker.py        — Builds momentum vectors per particle
├── trajectory_analyzer.py     — Classifies pairs and computes priority
├── simulation_report.py       — Generates final JSON report
└── run_simulation.py          — Orchestrates the pipeline
```

## Files Known to Be Correct

- `/app/runtime/trace_parser.py` — Parsing logic is verified correct
- `/app/runtime/run_simulation.py` — Orchestration logic is verified correct
- `/app/runtime/data/collision_trace.log` — Input data is verified correct

## Files Containing Bugs

- `/app/runtime/momentum_tracker.py` — Momentum tracking has an error
- `/app/runtime/trajectory_analyzer.py` — Trajectory analysis has errors
- `/app/runtime/simulation_report.py` — Report generation inherits analysis errors

## Output Schema

### simulation_state.jsonl

One JSON record per line. Particle state records:
```json
{"type": "particle_state", "particle_id": "particle_alpha", "momentum_vector": [...], "own_momentum": 15}
```

Event summary record:
```json
{"type": "event_summary", "total_events": 45, "per_particle": {"particle_alpha": 9, ...}}
```

### trajectory_report.json

```json
{
  "simulation_summary": {"particle_count": 7, "total_events": 45, "particles": [...]},
  "momentum_state": {"particle_alpha": {"vector": [...], "vector_sum": 51}, ...},
  "pair_classification": {"independent_pairs": [...], "dependent_pairs": [...], "independent_count": 21, "total_pairs": 21},
  "harvesting_priority": ["particle_epsilon", "particle_eta", "particle_zeta", ...],
  "validation": {"digest": "771f0d20bdcc7ffb"}
}
```

## Event Types

- **DRIFT**: Low-energy displacement, adds +1 to particle's own momentum
- **THRUST**: High-energy boost, adds +2 to particle's own momentum
- **COLLIDE**: Elastic collision with another particle, synchronizes momentum knowledge

## Constraints

- All particles start with BASE_MOMENTUM = 3
- There are 7 particles total with 45 events
- Particles that collide: alpha, beta, gamma, delta (1 collision each)
- Particles that never collide: epsilon, eta, zeta
