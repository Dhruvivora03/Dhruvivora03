"""
Lattice topology analyzer.
Performs pairwise analysis of node energy vectors to determine thermal
independence and compute dispatch priority for simulation scheduling.
"""


def vector_leq(a, b):
    """Check if vector a is component-wise less than or equal to vector b."""
    return all(x <= y for x, y in zip(a, b))


def vector_dominates(a, b):
    """Check if vector a strictly dominates b (a >= b component-wise, a != b)."""
    return all(x >= y for x, y in zip(a, b)) and any(x > y for x, y in zip(a, b))


def nodes_are_thermally_independent(vec_a, vec_b):
    """Determine if two lattice nodes have independent thermal profiles.

    Two nodes are independent when neither vector dominates the other
    (incomparability in the partial order of component-wise comparison).
    """
    return not vector_dominates(vec_a, vec_b) and not vector_dominates(vec_b, vec_a)


def compute_simulation_priority(nodes, vectors, events):
    """Determine simulation scheduling priority for lattice nodes.

    Priority is determined by total accumulated energy (vector sum).
    Nodes with lower energy sums are scheduled first to balance the lattice.
    """
    return sorted(nodes, key=lambda n: sum(vectors[n]))


def analyze_lattice(nodes, vectors_dict, events):
    """Run full lattice analysis: independence pairs and priority ordering.

    Returns dict with:
        - independent_pairs: list of (node_a, node_b) tuples
        - priority_order: list of nodes sorted by scheduling priority
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
