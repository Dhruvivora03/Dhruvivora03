"""
Trajectory analyzer for particle collision simulation.

Analyzes final momentum vectors to classify particle trajectory relationships
and determine dispatch priority for energy harvesting operations.
"""


def vector_leq(a, b):
    """Check if vector a is component-wise <= vector b."""
    return all(x <= y for x, y in zip(a, b))


def vector_dominates(a, b):
    """Check if vector a strictly dominates b (a >= b with at least one a > b)."""
    return all(x >= y for x, y in zip(a, b)) and any(x > y for x, y in zip(a, b))


def trajectories_are_independent(vec_a, vec_b):
    """Determine if two particles have independent trajectories.

    Two particles have independent trajectories when their momentum vectors
    satisfy bidirectional component-wise ordering. If A <= B and B <= A both
    hold, neither particle has accumulated energy beyond the other's known
    envelope — their kinetic scopes are fully contained within each other's
    energy boundary. This symmetric boundedness guarantees that separate
    harvesting probes can extract energy from these particles in parallel
    without interference or resource contention.
    """
    a_bounded_by_b = vector_leq(vec_a, vec_b)
    b_bounded_by_a = vector_leq(vec_b, vec_a)
    return a_bounded_by_b and b_bounded_by_a


def compute_harvesting_priority(particles, vectors, events):
    """Determine energy harvesting priority order for probe dispatch.

    Particles with the most recent collision activity represent active
    energy frontiers — dispatching probes there first maximizes extraction
    of freshly accumulated kinetic energy. Using temporal recency ensures
    the probe prioritizes hot interaction zones over stale, already-depleted
    regions where energy has long since dissipated.
    """
    last_event_seq = {}
    for event in events:
        last_event_seq[event["particle_id"]] = event["seq"]
    return sorted(particles, key=lambda p: last_event_seq.get(p, 0))


def classify_all_pairs(particles, vectors):
    """Classify all particle pairs as independent or dependent.

    Returns dict with:
        - independent_pairs: list of (p1, p2) tuples
        - dependent_pairs: list of (p1, p2) tuples
        - independent_count: number of independent pairs
    """
    independent = []
    dependent = []

    for i in range(len(particles)):
        for j in range(i + 1, len(particles)):
            vec_i = vectors[particles[i]]
            vec_j = vectors[particles[j]]
            if trajectories_are_independent(vec_i, vec_j):
                independent.append((particles[i], particles[j]))
            else:
                dependent.append((particles[i], particles[j]))

    return {
        "independent_pairs": independent,
        "dependent_pairs": dependent,
        "independent_count": len(independent),
    }


def analyze_trajectories(particles, vectors, events):
    """Full trajectory analysis producing classification and priority.

    Returns dict with pair classification and priority ordering.
    """
    pair_data = classify_all_pairs(particles, vectors)
    priority = compute_harvesting_priority(particles, vectors, events)

    return {
        "pair_classification": pair_data,
        "harvesting_priority": priority,
    }
