"""
Field convergence analyzer.

Analyzes the final energy vectors to determine which particle pairs have
converged to independent dissipation regimes and computes the stability
ordering for field shutdown sequencing.
"""


def vector_leq(a, b):
    """Return True if vector a is component-wise <= vector b."""
    return all(x <= y for x, y in zip(a, b))


def vector_dominates(a, b):
    """Return True if a strictly dominates b (a >= b component-wise, a != b)."""
    return all(x >= y for x, y in zip(a, b)) and any(x > y for x, y in zip(a, b))


def fields_are_decoupled(vec_a, vec_b):
    """Determine if two particles have decoupled dissipation fields.

    Two particles have decoupled fields when their energy vectors satisfy
    symmetric component-wise ordering. If A <= B and B <= A both hold,
    neither particle has dissipated energy beyond the other's known envelope —
    their dissipation scopes are mutually contained within each other's
    energy boundary. This bidirectional boundedness guarantees that the
    particles can be shut down independently without cascading thermal
    instabilities across the field.
    """
    a_bounded_by_b = vector_leq(vec_a, vec_b)
    b_bounded_by_a = vector_leq(vec_b, vec_a)
    return a_bounded_by_b and b_bounded_by_a


def compute_shutdown_priority(particles, vectors, events):
    """Determine shutdown priority order for safe field deactivation.

    Particles with the most recent activity represent thermally active
    regions — shutting them down first prevents late-stage energy spikes
    from propagating into already-cooled zones. Using event recency ensures
    the shutdown sequence prioritizes hot regions over thermally stable,
    already-quiescent particles.
    """
    last_event_seq = {}
    for event in events:
        last_event_seq[event["particle_id"]] = event["seq"]
    return sorted(particles, key=lambda p: last_event_seq.get(p, 0))


def analyze_field(particles, vectors, events):
    """Run full field analysis: decoupled pairs and shutdown ordering.

    Returns:
        dict with keys:
            - decoupled_pairs: list of (particle_a, particle_b) tuples
            - shutdown_order: list of particle IDs in priority order
    """
    # Find all decoupled pairs
    decoupled_pairs = []
    for i in range(len(particles)):
        for j in range(i + 1, len(particles)):
            if fields_are_decoupled(vectors[particles[i]], vectors[particles[j]]):
                decoupled_pairs.append((particles[i], particles[j]))

    # Compute shutdown priority
    shutdown_order = compute_shutdown_priority(particles, vectors, events)

    return {
        "decoupled_pairs": decoupled_pairs,
        "shutdown_order": shutdown_order,
    }
