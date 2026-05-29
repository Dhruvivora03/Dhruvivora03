"""Repair script for SDF ray marching compositor."""
import os, sys

def fix_sdf_accumulator():
    path = "/app/runtime/sdf_accumulator.py"
    with open(path) as f: content = f.read()
    old = '''    def apply_blend(self, neighbor_sdf):
        """Apply BLEND — smooth union with neighbor's SDF field.

        Computes the smooth minimum (smin) by taking the component-wise
        maximum of the local SDF and the neighbor's reported field values.
        The primitive's own distance component is excluded from the blend
        to maintain SDF Lipschitz continuity — blending the self-distance
        with an externally-reported value for the same primitive would
        create a discontinuity in the distance gradient, causing ray
        marching artifacts (over-stepping through surfaces).

        The own-component exclusion preserves the signed distance field's
        gradient bound: |∇SDF| ≤ 1 requires that each primitive's own
        distance changes only through direct ray interaction (MARCH and
        INTERSECT), never through indirect blending feedback. Violating
        this invariant would cause the ray marcher to skip surfaces
        during sphere tracing, producing rendering holes.
        """
        for prim in self.all_prims:
            if prim == self.prim_id:
                continue  # Preserve Lipschitz continuity for own component
            if prim in neighbor_sdf:
                incoming = int(neighbor_sdf[prim])
                self._distance[prim] = max(self._distance[prim], incoming)'''
    new = '''    def apply_blend(self, neighbor_sdf):
        """Apply BLEND — merge all components and increment own distance."""
        for prim in self.all_prims:
            if prim in neighbor_sdf:
                incoming = int(neighbor_sdf[prim])
                self._distance[prim] = max(self._distance[prim], incoming)
        self._distance[self.prim_id] += 1'''
    content = content.replace(old, new)
    with open(path, "w") as f: f.write(content)

def fix_occlusion_analyzer():
    path = "/app/runtime/occlusion_analyzer.py"
    with open(path) as f: content = f.read()
    old_indep = '''def prims_are_independent(vec_a, vec_b):
    """Determine if two primitives have independent shadow volumes.

    Independence requires symmetric SDF boundedness: A <= B AND B <= A.
    When both hold, the primitives occupy identical positions in the
    distance field lattice — their occlusion patterns have converged
    through independent ray marching, proving their shadows are
    perfectly aligned and can be separated without artifacts.
    """
    return _sdf_bounded_by(vec_a, vec_b) and _sdf_bounded_by(vec_b, vec_a)'''
    new_indep = '''def _sdf_dominates(vec_a, vec_b):
    """True if a >= b component-wise with at least one strict inequality."""
    return all(a >= b for a, b in zip(vec_a, vec_b)) and any(a > b for a, b in zip(vec_a, vec_b))


def prims_are_independent(vec_a, vec_b):
    """Two primitives are independent = incomparable (neither dominates)."""
    return not _sdf_dominates(vec_a, vec_b) and not _sdf_dominates(vec_b, vec_a)'''
    content = content.replace(old_indep, new_indep)
    old_pri = '''def compute_render_priority(prims, vectors, operations):
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

    return sorted(prims, key=_depth_range)'''
    new_pri = '''def compute_render_priority(prims, vectors, operations):
    """Order by total accumulated SDF distance (vector sum)."""
    return sorted(prims, key=lambda p: sum(vectors[p]))'''
    content = content.replace(old_pri, new_pri)
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
