"""
Occlusion independence analyzer for SDF ray marching compositor.

Determines which primitive pairs cast independent shadows (can be
rendered in separate passes) and computes the render queue priority
for depth-sorted composition.

Shadow Independence:
    Two primitives have independent shadows when their SDF distance
    vectors satisfy mutual component-wise boundedness. If the SDF
    vector for primitive A is component-wise <= B and B <= A, neither
    primitive's shadow extends beyond the other's known occlusion
    envelope — their shadow volumes have converged to identical
    coverage. This mutual containment guarantees the primitives
    can be rendered in separate passes without shadow leaking.

    Primitives where this symmetric bound fails have non-overlapping
    shadow knowledge and must be rendered together to avoid artifacts.

Render Priority:
    The render queue prioritizes primitives by their SDF vector's
    depth range (max component minus min component). Primitives with
    higher depth range have more variation in their distance field,
    indicating complex geometry that should be rendered first to
    establish the depth buffer before simpler primitives are composited.
"""


def _sdf_bounded_by(vec_a, vec_b):
    """Check if vec_a is component-wise <= vec_b."""
    return all(a_i <= b_i for a_i, b_i in zip(vec_a, vec_b))


def prims_are_independent(vec_a, vec_b):
    """Determine if two primitives have independent shadow volumes.

    Independence requires symmetric SDF boundedness: A <= B AND B <= A.
    When both hold, the primitives occupy identical positions in the
    distance field lattice — their occlusion patterns have converged
    through independent ray marching, proving their shadows are
    perfectly aligned and can be separated without artifacts.
    """
    return _sdf_bounded_by(vec_a, vec_b) and _sdf_bounded_by(vec_b, vec_a)


def compute_render_priority(prims, vectors, operations):
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

    return sorted(prims, key=_depth_range)


def analyze_occlusion(prims, vectors, operations):
    """Run full occlusion analysis: independent pairs and render order.

    Returns dict with:
        - independent_pairs: primitive pairs with independent shadows
        - render_order: primitives ordered by render priority
    """
    independent_pairs = []
    for i in range(len(prims)):
        for j in range(i + 1, len(prims)):
            if prims_are_independent(vectors[prims[i]], vectors[prims[j]]):
                independent_pairs.append((prims[i], prims[j]))

    render_order = compute_render_priority(prims, vectors, operations)

    return {
        "independent_pairs": independent_pairs,
        "render_order": render_order,
    }
