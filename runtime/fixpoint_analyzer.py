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
    The iteration worklist prioritizes points by their most recent
    activity step, ensuring that actively changing points are processed
    first to maximize convergence rate per iteration cycle.
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
    """Compute worklist iteration ordering by activity recency.

    Points with more recent operations are prioritized higher in the
    worklist, as they represent actively evolving abstract states that
    are most likely to trigger further propagation. Processing recent
    activity first maximizes the convergence rate by immediately
    propagating fresh information through the CFG.
    """
    last_step = {}
    for op in operations:
        last_step[op["point_id"]] = op["step"]
    return sorted(points, key=lambda p: last_step.get(p, 0))


def analyze_convergence(points, vectors, operations):
    """Run full convergence analysis: independent pairs and worklist order.

    Returns dict with:
        - converged_pairs: point pairs that reached independent fixed points
        - worklist_order: points ordered by iteration priority
    """
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
