# SDF Ray Marching Compositor — Debugging Task

## Overview

A signed distance field (SDF) ray marching compositor renders a scene with 7 CSG primitives. Each primitive accumulates march distance through ray operations (MARCH, INTERSECT) and blends SDF knowledge from neighboring primitives via BLEND operations for smooth union composition.

The pipeline performs these steps:
1. Parses the scene trace from `/app/runtime/data/scene_trace.log`
2. Processes each operation through the SDF accumulator (`/app/runtime/sdf_accumulator.py`)
3. Computes occlusion analysis (`/app/runtime/occlusion_analyzer.py`)
4. Writes state to `/app/runtime/sdf_state.jsonl`
5. Writes the render report to `/app/runtime/render_report.jsonl`

## Observed Problem

The compositor runs without errors but produces incorrect results:

- The occlusion report shows **0 independent pairs** when analysis expects **14** out of 21 possible pairs
- The render ordering does not reflect total accumulated SDF distance
- sphere_a's own SDF component reports **12** but integration of its operation history (4 MARCH + 2 INTERSECT + 2 BLEND) suggests it should be **14**
- The report digest is `956f88a30280dbc4` instead of the expected `eb349cdee629424d`

## Expected Behavior

When all bugs are fixed, the pipeline should:

1. **SDF Accumulator (`/app/runtime/sdf_accumulator.py`)**: Each BLEND operation should merge ALL components of the neighbor SDF state (including the primitive's own component via component-wise maximum), then increment the primitive's own component by 1. The own component must participate in the blend to absorb any neighbor knowledge about this primitive's distance.

2. **Occlusion Analysis (`/app/runtime/occlusion_analyzer.py`)**: Two primitives have independent shadow volumes when their SDF vectors are *incomparable* in the partial order — meaning neither vector dominates the other component-wise. This indicates they cast shadows through independent geometry.

3. **Render Priority (`/app/runtime/occlusion_analyzer.py`)**: Primitives should be ordered by total SDF distance (vector sum) to prioritize rendering of primitives with the highest accumulated march distance.

## File Layout

```
/app/runtime/
├── data/
│   └── scene_trace.log        # Scene trace (correct, do not modify)
├── scene_parser.py            # Trace parser (correct, do not modify)
├── sdf_accumulator.py         # SDF distance engine (contains bug)
├── occlusion_analyzer.py      # Shadow analysis (contains bugs)
├── render_report.py           # Report generation (affected by analyzer bugs)
└── run_compositor.py          # Orchestrator (correct, do not modify)
```

## Correct Files (do not modify)

- `/app/runtime/data/scene_trace.log` — the raw scene trace in hash-separated format
- `/app/runtime/scene_parser.py` — parses trace into structured operation records
- `/app/runtime/run_compositor.py` — orchestrates the full compositor pipeline

## Files With Bugs

- `/app/runtime/sdf_accumulator.py` — SDF distance vector computation during BLEND
- `/app/runtime/occlusion_analyzer.py` — shadow independence predicate and render ordering
- `/app/runtime/render_report.py` — report writer (cascading from analyzer bugs)

## Output Schema

### `/app/runtime/sdf_state.jsonl`

One JSON object per line, one per primitive (7 total):

```json
{"prim_id": "sphere_a", "sdf_vector": [10, 9, 10, 10, 9, 14, 10], "vector_sum": 72}
{"prim_id": "box_b", "sdf_vector": [13, 3, 3, 3, 3, 9, 3], "vector_sum": 37}
{"prim_id": "torus_c", "sdf_vector": [8, 9, 8, 9, 9, 9, 12], "vector_sum": 64}
{"prim_id": "cone_d", "sdf_vector": [8, 3, 12, 3, 3, 9, 3], "vector_sum": 41}
{"prim_id": "capsule_e", "sdf_vector": [3, 9, 3, 3, 3, 3, 3], "vector_sum": 27}
{"prim_id": "cylinder_f", "sdf_vector": [8, 9, 8, 10, 9, 9, 8], "vector_sum": 61}
{"prim_id": "plane_g", "sdf_vector": [3, 3, 3, 3, 9, 3, 3], "vector_sum": 27}
```

Vector component order corresponds to sorted primitive IDs: `[box_b, capsule_e, cone_d, cylinder_f, plane_g, sphere_a, torus_c]`.

### `/app/runtime/render_report.jsonl`

```json
{"prim_id": "...", "sdf_vector": [...], "type": "prim_state", "vector_sum": N}
...
{"independent_count": 14, "independent_pairs": [[...], ...], "render_order": ["capsule_e", "plane_g", "box_b", "cone_d", "cylinder_f", "torus_c", "sphere_a"], "type": "occlusion_analysis"}
{"fingerprint": "eb349cdee629424d", "type": "digest"}
```

## Expected Correct Values

| Metric | Expected Value |
|--------|---------------|
| sphere_a own SDF component | **14** |
| Total independent pairs | **14** (out of 21 possible) |
| Render order (last = highest priority) | **sphere_a** (sum = 72) |
| Render order (first = lowest priority) | **capsule_e** (sum = 27) |
| Report fingerprint digest | `eb349cdee629424d` |
