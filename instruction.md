# GPU Shader Pipeline Profiler — Debugging Task

## Overview

A GPU shader pipeline profiler monitors 7 shader stages in a rendering pipeline, tracking their accumulated execution cycles through sample ticks, burst measurements, and synchronization events. The profiler reads a trace log, builds per-shader cycle vectors, classifies pipeline stage relationships, and generates a report with scheduling priority for workload redistribution.

The profiler is producing incorrect results. Several output values do not match expected values from validated reference runs.

## Observed Symptoms

1. **Cycle counts too low**: Shader vertex should have own cycles of **15** after all events, but the profiler reports **14**. Similarly, shader fragment reports 11 instead of expected 12, geometry reports 8 instead of 9, and tessctl reports 10 instead of 11.

2. **No disjoint pairs detected**: The pipeline report shows 0 disjoint shader pairs, but the expected count is **21** (all pairs should be disjoint given the pipeline stage isolation).

3. **Wrong scheduling priority**: The priority list starts with `shader_geometry` and ends with `shader_fragment`, but correct ordering should start with a low-cycle shader (`shader_compute`) and end with a high-cycle shader (`shader_vertex`).

4. **Digest mismatch**: Expected digest is `58116a4dfeeaa55e`, profiler produces `3218f2f9f54ead88`.

## File Layout

All runtime files are located at `/app/runtime/`:

```
/app/runtime/
├── data/
│   └── profile_log.dat        — Profiling trace (input data)
├── log_reader.py              — Parses trace log into events
├── cycle_counter.py           — Builds cycle vectors per shader
├── pipeline_analyzer.py       — Classifies pairs and computes priority
├── profiling_report.py        — Generates final JSON report
└── run_profiler.py            — Orchestrates the pipeline
```

## Files Known to Be Correct

- `/app/runtime/log_reader.py` — Parsing logic is verified correct
- `/app/runtime/run_profiler.py` — Orchestration logic is verified correct
- `/app/runtime/data/profile_log.dat` — Input data is verified correct

## Files Containing Bugs

- `/app/runtime/cycle_counter.py` — Cycle tracking has an error
- `/app/runtime/pipeline_analyzer.py` — Pipeline analysis has errors
- `/app/runtime/profiling_report.py` — Report generation inherits analysis errors

## Output Schema

### profiler_state.jsonl

One JSON record per line. Shader state records:
```json
{"type": "shader_state", "shader_id": "shader_vertex", "cycle_vector": [...], "own_cycles": 15}
```

Event summary record:
```json
{"type": "event_summary", "total_events": 45, "per_shader": {"shader_vertex": 9, ...}}
```

### pipeline_report.json

```json
{
  "profiling_summary": {"shader_count": 7, "total_events": 45, "shaders": [...]},
  "cycle_state": {"shader_vertex": {"vector": [...], "vector_sum": 51}, ...},
  "pair_classification": {"disjoint_pairs": [...], "coupled_pairs": [...], "disjoint_count": 21, "total_pairs": 21},
  "scheduling_priority": ["shader_compute", "shader_raytrace", "shader_tesseval", ...],
  "validation": {"digest": "58116a4dfeeaa55e"}
}
```

## Event Types

- **SAMPLE**: Single-frame profiling tick, adds +1 to shader's own cycles
- **BURST**: Multi-frame profiling burst, adds +2 to shader's own cycles
- **SYNC**: Synchronization with adjacent pipeline stage, propagates cycle knowledge

## Constraints

- All shaders start with BASE_CYCLES = 3
- There are 7 shader stages with 45 total profiling events
- Shaders that sync: vertex, fragment, geometry, tessctl (1 sync each)
- Shaders that never sync: compute, raytrace, tesseval
