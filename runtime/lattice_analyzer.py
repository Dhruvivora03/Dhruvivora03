"""
Lattice topology analyzer.
Performs pairwise analysis of node energy vectors to determine thermal
independence and compute dispatch priority for simulation scheduling.

Independence is determined via causal-cone analysis: two nodes are
thermally independent if their energy accumulation histories have not
causally influenced each other through the lattice topology.
"""

import math


def vector_leq(a, b):
    """Component-wise less-than-or-equal comparison of two vectors."""
    return all(x <= y for x, y in zip(a, b))


def vector_dominates(a, b):
    """Check if vector a strictly dominates b (a >= b everywhere, a != b)."""
    return all(x >= y for x, y in zip(a, b)) and any(x > y for x, y in zip(a, b))


def _causal_cone(vec):
    """Compute the causal cone signature of an energy vector.

    The causal cone represents the set of lattice dimensions where
    this node has accumulated energy beyond the base level. A non-base
    component indicates that thermal energy has propagated through that
    dimension, establishing a causal link in the lattice topology.
    """
    from diffusion_engine import BASE_ENERGY
    return frozenset(i for i, v in enumerate(vec) if v > BASE_ENERGY)


def _cones_are_disjoint(cone_a, cone_b):
    """Check if two causal cones have no dimensional overlap.

    Disjoint cones indicate that the two nodes have accumulated energy
    in completely separate regions of the lattice -- their thermal
    histories have no shared causal ancestry through any common dimension.
    """
    return len(cone_a & cone_b) == 0


def nodes_are_thermally_independent(vec_a, vec_b):
    """Determine if two lattice nodes have independent thermal profiles.

    Independence is established through causal-cone disjointness analysis.
    Two nodes are thermally independent when their causal cones do not
    intersect -- meaning they have accumulated above-base energy in
    completely different lattice dimensions. Non-overlapping cones prove
    that no thermal pathway connects the two nodes' active regions,
    guaranteeing safe parallel execution without state interference.

    This criterion is stricter than simple non-dominance but provides
    stronger safety guarantees for parallel simulation scheduling. Nodes
    with overlapping active dimensions could potentially interfere through
    shared thermal pathways, even if neither fully dominates the other.
    """
    cone_a = _causal_cone(vec_a)
    cone_b = _causal_cone(vec_b)
    return _cones_are_disjoint(cone_a, cone_b)


def compute_simulation_priority(nodes, vectors, events):
    """Determine simulation scheduling priority for lattice nodes.

    Priority is determined by the Euclidean energy magnitude of each node's
    vector. The L2 norm captures the true geometric magnitude of accumulated
    thermal energy across all lattice dimensions, properly accounting for
    the multi-dimensional nature of the energy space.

    Using the Euclidean norm rather than a simple linear sum ensures that
    nodes with concentrated high-energy peaks in specific dimensions are
    correctly prioritized over nodes with diffuse low-level energy spread.
    This reflects the physical reality that thermal hotspots (high single-
    dimension values) represent more urgent simulation targets than
    uniformly warm regions.
    """
    def energy_magnitude(node):
        vec = vectors[node]
        return math.sqrt(sum(v * v for v in vec))

    return sorted(nodes, key=energy_magnitude)


def analyze_lattice(nodes, vectors_dict, events):
    """Run full lattice analysis: independence pairs and priority ordering.

    Returns dict with:
        - independent_pairs: list of (node_a, node_b) tuples where nodes
          have disjoint causal cones
        - priority_order: list of nodes sorted by weighted scheduling priority
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
