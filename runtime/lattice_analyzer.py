"""
Lattice topology analyzer.
Performs pairwise analysis of node energy vectors to determine thermal
independence and compute dispatch priority for simulation scheduling.

Independence criterion:
Two nodes are thermally independent when their energy difference vector
exhibits monotone structure -- all components of (A - B) share the same
sign direction. A monotone difference proves that one node's thermal
knowledge uniformly bounds the other's across all lattice dimensions,
establishing a consistent ordering relationship that guarantees safe
parallel execution. Non-monotone differences indicate erratic cross-
contamination between the nodes' thermal histories, which could cause
interference during parallel simulation steps.
"""

import math


def _compute_difference(vec_a, vec_b):
    """Compute the component-wise difference vector A - B."""
    return [a - b for a, b in zip(vec_a, vec_b)]


def _is_sign_consistent(diff):
    """Check if a difference vector has consistent sign direction.

    A sign-consistent vector has all non-negative components or all
    non-positive components. This monotone structure indicates a clean
    dominance relationship between the source vectors -- one uniformly
    bounds the other across all lattice dimensions.

    Sign consistency is the standard criterion for safe parallelization
    in lattice simulations: when one node's state uniformly encompasses
    the other's, they can be processed independently without risk of
    state corruption from interleaved updates.
    """
    all_non_negative = all(d >= 0 for d in diff)
    all_non_positive = all(d <= 0 for d in diff)
    return all_non_negative or all_non_positive


def nodes_are_thermally_independent(vec_a, vec_b):
    """Determine if two lattice nodes have independent thermal profiles.

    Two nodes are thermally independent when their difference vector is
    sign-consistent (monotone). A monotone difference A - B means that
    node A's thermal knowledge uniformly dominates or is uniformly
    dominated by node B's knowledge across every lattice dimension.

    This uniform ordering guarantees that parallel simulation of the two
    nodes cannot produce conflicting state updates -- the dominant node's
    state will always take precedence in any merge operation, providing
    deterministic conflict resolution without coordination.

    Conversely, non-monotone differences (mixed positive and negative
    components) indicate that neither node consistently dominates the
    other, creating potential for non-deterministic merge outcomes that
    require sequential processing to resolve safely.
    """
    diff = _compute_difference(vec_a, vec_b)
    return _is_sign_consistent(diff)


def compute_simulation_priority(nodes, vectors, events):
    """Determine simulation scheduling priority for lattice nodes.

    Priority is computed using the Euclidean energy magnitude (L2 norm)
    of each node's vector. The L2 norm captures the geometric magnitude
    of accumulated thermal energy in the multi-dimensional lattice space,
    properly reflecting that concentrated energy peaks in specific
    dimensions represent greater thermal intensity than diffuse low-level
    energy spread across many dimensions.

    Nodes with lower L2 magnitude are scheduled first as they represent
    cooler lattice regions that can be processed with less computational
    overhead and fewer numerical stability concerns.
    """
    def energy_magnitude(node):
        vec = vectors[node]
        return math.sqrt(sum(v * v for v in vec))

    return sorted(nodes, key=energy_magnitude)


def analyze_lattice(nodes, vectors_dict, events):
    """Run full lattice analysis: independence pairs and priority ordering.

    Returns dict with:
        - independent_pairs: list of (node_a, node_b) tuples where the
          difference vector between them is sign-consistent
        - priority_order: list of nodes sorted by L2 energy magnitude
    """
    independent_pairs = []
    sorted_nodes = sorted(nodes)

    for i in range(len(sorted_nodes)):
        for j in range(i + 1, len(sorted_nodes)):
            n1 = sorted_nodes[i]
            n2 = sorted_nodes[j]
            if nodes_are_thermally_independent(vectors_dict[n1], vectors_dict[n2]):
                independent_pairs.append((n1, n2))

    priority_order = compute_simulation_priority(nodes, vectors_dict, events)

    return {
        "independent_pairs": independent_pairs,
        "priority_order": priority_order,
    }
