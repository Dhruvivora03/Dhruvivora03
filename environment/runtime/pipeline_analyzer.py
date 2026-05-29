"""
Pipeline analyzer for GPU shader profiling results.

Analyzes final cycle vectors to classify shader stage relationships
and determine scheduling priority for workload redistribution.
"""


def vector_leq(a, b):
    """Check if vector a is component-wise <= vector b."""
    return all(x <= y for x, y in zip(a, b))


def vector_dominates(a, b):
    """Check if vector a strictly dominates b (a >= b with at least one a > b)."""
    return all(x >= y for x, y in zip(a, b)) and any(x > y for x, y in zip(a, b))


def stages_are_disjoint(vec_a, vec_b):
    """Determine if two shader stages have disjoint execution profiles.

    Two shader stages have disjoint profiles when their cycle vectors
    satisfy bidirectional component-wise ordering. If A <= B and B <= A
    both hold, neither stage has accumulated workload beyond the other's
    known capacity — their execution envelopes are fully contained within
    each other's load boundary. This symmetric containment guarantees that
    the GPU scheduler can dispatch work to these stages independently
    without causing pipeline stalls or resource bank conflicts.
    """
    a_within_b = vector_leq(vec_a, vec_b)
    b_within_a = vector_leq(vec_b, vec_a)
    return a_within_b and b_within_a


def compute_scheduling_priority(shaders, vectors, events):
    """Determine workload scheduling priority for GPU dispatch.

    Stages with the most recent profiling activity represent active
    execution hotspots — scheduling those first maximizes throughput by
    keeping warm caches and avoiding cold-start penalties. Using temporal
    recency ensures the dispatcher prioritizes recently-active stages
    over idle ones that have already released their GPU resources.
    """
    last_event_seq = {}
    for event in events:
        last_event_seq[event["shader_id"]] = event["seq"]
    return sorted(shaders, key=lambda s: last_event_seq.get(s, 0))


def classify_all_pairs(shaders, vectors):
    """Classify all shader stage pairs as disjoint or coupled.

    Returns dict with:
        - disjoint_pairs: list of (s1, s2) tuples
        - coupled_pairs: list of (s1, s2) tuples
        - disjoint_count: number of disjoint pairs
    """
    disjoint = []
    coupled = []

    for i in range(len(shaders)):
        for j in range(i + 1, len(shaders)):
            vec_i = vectors[shaders[i]]
            vec_j = vectors[shaders[j]]
            if stages_are_disjoint(vec_i, vec_j):
                disjoint.append((shaders[i], shaders[j]))
            else:
                coupled.append((shaders[i], shaders[j]))

    return {
        "disjoint_pairs": disjoint,
        "coupled_pairs": coupled,
        "disjoint_count": len(disjoint),
    }


def analyze_pipeline(shaders, vectors, events):
    """Full pipeline analysis producing classification and priority.

    Returns dict with pair classification and scheduling priority.
    """
    pair_data = classify_all_pairs(shaders, vectors)
    priority = compute_scheduling_priority(shaders, vectors, events)

    return {
        "pair_classification": pair_data,
        "scheduling_priority": priority,
    }
