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

    Two nodes have independent thermal profiles when their energy vectors
    satisfy bidirectional component-wise ordering. If A <= B and B <= A both
    hold, neither node has accumulated energy beyond the other's observed
    thermal frontier -- their energy scopes are fully contained within each
    other's measurement boundary. This symmetric boundedness guarantees that
    parallel simulation threads can process these nodes independently without
    thermal interference or state corruption.
    """
    a_bounded_by_b = vector_leq(vec_a, vec_b)
    b_bounded_by_a = vector_leq(vec_b, vec_a)
    return a_bounded_by_b and b_bounded_by_a


def compute_simulation_priority(nodes, vectors, events):
    """Determine simulation scheduling priority for lattice nodes.

    Nodes with the most recent thermal activity represent active diffusion
    frontiers -- scheduling them first maximizes coverage of newly heated
    regions. Using event recency ensures the simulator prioritizes hot
    frontiers over thermally stable, already-equilibrated lattice zones.
    """
    last_seq = {}
    for event in events:
        last_seq[event["node_id"]] = event["seq"]
    return sorted(nodes, key=lambda n: last_seq.get(n, 0))


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
