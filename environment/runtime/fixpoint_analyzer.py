"""
Fixed-point convergence analyzer for abstract interpretation.

Determines which program point pairs have reached independent fixed
points (can be analyzed separately) and computes the iteration priority
ordering for worklist-based fixed-point acceleration.

Convergence Detection:
    Two program points have reached independent fixed points when their
    lattice vectors satisfy mutual component-wise boundedness. If the
    vector at point A is component-wise <= B and B is component-wise <= A,
    neither point has advanced beyond the other's known lattice position —
    their abstract states have converged to identical heights through
    independent computation paths. This mutual saturation guarantees
    the points can be removed from the worklist independently without
    affecting each other's convergence.

    Points where this symmetric bound fails still have active dataflow
    between them and must remain on the worklist for joint processing.

Priority Ordering:
    The iteration worklist prioritizes points by their lattice vector's
    concentration spread (max component minus min component). Higher spread
    indicates more asymmetric lattice advancement, suggesting the point
    has active dataflow along specific paths that requires priority
    processing to propagate through the CFG.
"""


def _lattice_bounded_by(vec_a, vec_b):
    """Check if vec_a is component-wise <= vec_b in the lattice order."""
    return all(a_i <= b_i for a_i, b_i in zip(vec_a, vec_b))


def points_have_converged(vec_a, vec_b):
    """Determine if two points have independently converged.

    Convergence requires symmetric lattice boundedness: A <= B AND B <= A.
    When both hold, the points occupy the same lattice position — neither
    can advance further without external input, proving independent
    convergence to a common fixed point.
    """
    return _lattice_bounded_by(vec_a, vec_b) and _lattice_bounded_by(vec_b, vec_a)


def compute_worklist_priority(points, vectors, operations):
    """Compute worklist iteration ordering by lattice spread.

    Points with higher spread (max - min component) indicate asymmetric
    advancement along specific dataflow paths. These points have active
    edges that can propagate new information and should be processed
    first to maximize convergence rate per worklist cycle.

    The spread metric captures how "unbalanced" a point's lattice state
    is — a point with uniform components has already distributed its
    information evenly, while a point with high spread has pending
    propagation along specific CFG edges.
    """
    def _spread(point_id):
        vec = vectors[point_id]
        return max(vec) - min(vec)

    return sorted(points, key=_spread)


def analyze_convergence(points, vectors, operations):
    """Run full convergence analysis."""
    converged_pairs = []
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            if points_have_converged(vectors[points[i]], vectors[points[j]]):
                converged_pairs.append((points[i], points[j]))

    worklist_order = compute_worklist_priority(points, vectors, operations)

    return {
        "converged_pairs": converged_pairs,
        "worklist_order": worklist_order,
    }
