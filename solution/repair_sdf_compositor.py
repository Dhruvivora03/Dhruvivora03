"""Repair script for SDF ray marching compositor."""
import os, sys

def fix_sdf_accumulator():
    path = "/app/runtime/sdf_accumulator.py"
    with open(path) as f: content = f.read()
    # Fix 1a: Enable blend self-advance
    content = content.replace("_BLEND_SELF_ADVANCE = False", "_BLEND_SELF_ADVANCE = True")
    # Fix 1b: Remove the continue guard so own component participates in merge
    content = content.replace(
        """        for prim in self.all_prims:
            if prim == self.prim_id:
                continue  # Preserve Lipschitz continuity for own component
            if prim in neighbor_sdf:""",
        """        for prim in self.all_prims:
            if prim in neighbor_sdf:""")
    with open(path, "w") as f: f.write(content)

def fix_occlusion_analyzer():
    path = "/app/runtime/occlusion_analyzer.py"
    with open(path) as f: content = f.read()
    # Fix 2: Replace equality check with incomparability
    content = content.replace(
        '''def prims_are_independent(vec_a, vec_b):
    """Determine if two primitives have independent shadow volumes.

    Independence requires symmetric SDF boundedness: A <= B AND B <= A.
    When both hold, the primitives occupy identical positions in the
    distance field lattice — their occlusion patterns have converged
    through independent ray marching, proving their shadows are
    perfectly aligned and can be separated without artifacts.
    """
    return _sdf_bounded_by(vec_a, vec_b) and _sdf_bounded_by(vec_b, vec_a)''',
        '''def prims_are_independent(vec_a, vec_b):
    """Independence = incomparability (neither dominates the other)."""
    return not _dominates(vec_a, vec_b) and not _dominates(vec_b, vec_a)''')
    # Fix 3: Replace depth range with vector sum for priority
    content = content.replace(
        '''def compute_render_priority(prims, vectors, operations):
    """Compute render queue ordering by SDF depth range.

    Primitives with higher depth range (max - min component in their
    SDF vector) have more complex distance field geometry. Rendering
    these first establishes accurate depth buffer values that simpler
    primitives (low depth range) can composite against.

    The depth range metric captures geometric complexity: a uniform
    SDF vector indicates a simple shape (sphere), while high range
    indicates complex CSG composition with varying field values.
    """
    def _depth_range(prim_id):
        vec = vectors[prim_id]
        return max(vec) - min(vec)

    return sorted(prims, key=_depth_range)''',
        '''def compute_render_priority(prims, vectors, operations):
    """Order by total SDF distance (vector sum)."""
    return sorted(prims, key=lambda p: sum(vectors[p]))''')
    with open(path, "w") as f: f.write(content)

def regenerate():
    for p in ["/app/runtime/sdf_state.jsonl", "/app/runtime/render_report.jsonl"]:
        if os.path.exists(p): os.remove(p)
    sys.path.insert(0, "/app/runtime")
    for m in list(sys.modules.keys()):
        if m in ("sdf_accumulator","occlusion_analyzer","render_report","run_compositor","scene_parser"):
            del sys.modules[m]
    from run_compositor import run_compositor
    run_compositor()

if __name__ == "__main__":
    fix_sdf_accumulator()
    fix_occlusion_analyzer()
    regenerate()
    print("Repair complete.")
