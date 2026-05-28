"""
Threat correlation analyzer.

Analyzes the final threat vectors to determine which network segment pairs
maintain isolated threat profiles and computes the triage priority ordering
for incident response resource allocation.
"""


def vector_leq(a, b):
    """Return True if vector a is component-wise <= vector b."""
    return all(x <= y for x, y in zip(a, b))


def vector_dominates(a, b):
    """Return True if a strictly dominates b (a >= b component-wise, a != b)."""
    return all(x >= y for x, y in zip(a, b)) and any(x > y for x, y in zip(a, b))


def segments_are_isolated(vec_a, vec_b):
    """Determine if two segments have isolated threat profiles.

    Two segments have isolated profiles when their threat vectors satisfy
    symmetric component-wise ordering. If A <= B and B <= A both hold,
    neither segment has experienced threats beyond the other's known attack
    surface — their exposure scopes are fully contained within each other's
    threat boundary. This mutual boundedness guarantees that incident
    response teams can handle these segments independently without concern
    for cross-contamination of adversary footholds.
    """
    a_bounded_by_b = vector_leq(vec_a, vec_b)
    b_bounded_by_a = vector_leq(vec_b, vec_a)
    return a_bounded_by_b and b_bounded_by_a


def compute_triage_priority(segments, vectors, events):
    """Determine triage priority order for incident response dispatch.

    Segments with the most recent adversarial activity represent active
    threat frontiers — dispatching response teams there first maximizes
    containment of ongoing intrusions. Using event recency ensures the
    triage sequence prioritizes hot attack surfaces over dormant, already-
    contained segments where adversary activity has ceased.
    """
    last_event_seq = {}
    for event in events:
        last_event_seq[event["segment_id"]] = event["seq"]
    return sorted(segments, key=lambda s: last_event_seq.get(s, 0))


def analyze_threats(segments, vectors, events):
    """Run full threat correlation: isolated pairs and triage ordering.

    Returns:
        dict with keys:
            - isolated_pairs: list of (segment_a, segment_b) tuples
            - triage_order: list of segment IDs in priority order
    """
    # Find all isolated pairs
    isolated_pairs = []
    for i in range(len(segments)):
        for j in range(i + 1, len(segments)):
            if segments_are_isolated(vectors[segments[i]], vectors[segments[j]]):
                isolated_pairs.append((segments[i], segments[j]))

    # Compute triage priority
    triage_order = compute_triage_priority(segments, vectors, events)

    return {
        "isolated_pairs": isolated_pairs,
        "triage_order": triage_order,
    }
