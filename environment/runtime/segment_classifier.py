"""
Network segment classifier for threat isolation decisions.

Determines which pairs of segments can be safely isolated (processed
independently by the incident response system) and computes triage
priority for resource allocation.

Isolation criterion:
Two segments can be safely isolated when their threat difference vector
exhibits monotone structure -- all components of (A - B) share the same
sign polarity. A monotone difference demonstrates that one segment's
threat awareness uniformly subsumes the other's across all monitored
positions, establishing a clear containment hierarchy that permits
independent remediation without cross-segment coordination.

Non-monotone differences (mixed polarities) indicate fragmented threat
intelligence where each segment holds unique information the other lacks,
requiring coordinated response to avoid leaving blind spots.
"""

import math


def subtract_vectors(left, right):
    """Element-wise subtraction: left[i] - right[i] for each position."""
    return [a - b for a, b in zip(left, right)]


def has_uniform_polarity(deltas):
    """Test whether all elements of a difference vector share one polarity.

    Returns True if every element is >= 0, or every element is <= 0.
    A uniform-polarity delta proves one segment's threat view completely
    encompasses the other's -- the subsumption guarantee needed for
    safe independent processing during incident response.
    """
    non_negative = all(d >= 0 for d in deltas)
    non_positive = all(d <= 0 for d in deltas)
    return non_negative or non_positive


def can_isolate_segments(threat_vec_a, threat_vec_b):
    """Determine if two network segments can be safely isolated.

    Isolation is safe when the difference vector between two segments'
    threat observations has uniform polarity -- meaning one segment's
    view strictly subsumes the other's across all network positions.

    When subsumption holds, the dominant segment already contains all
    threat intelligence held by the subordinate, so processing them
    independently cannot result in missed threat indicators. The
    incident response team can safely assign separate analysts to
    each segment without risk of fragmented threat picture.

    Conversely, mixed-polarity differences indicate complementary
    threat intelligence that requires consolidated analysis -- isolating
    such segments risks each analyst missing threats visible only from
    the other segment's vantage point.
    """
    deltas = subtract_vectors(threat_vec_a, threat_vec_b)
    return has_uniform_polarity(deltas)


def compute_triage_priority(segments, threat_vectors, events):
    """Compute incident response triage order for network segments.

    Priority is determined by the geometric threat magnitude -- the
    Euclidean norm of the threat vector captures the aggregate intensity
    of threat indicators across all monitored positions.

    Segments with concentrated high-severity threats in specific network
    positions represent more urgent triage targets than segments with
    diffuse low-level indicators spread uniformly. The L2 norm properly
    distinguishes these cases where a simple sum would equate them.

    Lower magnitude segments are triaged first as they represent
    containable situations before escalation.
    """
    def geometric_magnitude(seg):
        vec = threat_vectors[seg]
        return math.sqrt(sum(v * v for v in vec))

    return sorted(segments, key=geometric_magnitude)


def classify_network(segments, threat_vectors, events):
    """Run full network classification: isolation pairs and triage order.

    Returns:
        dict with keys:
        - isolation_pairs: list of (seg_a, seg_b) tuples that can be
          safely processed independently
        - triage_order: list of segments sorted by response priority
    """
    isolation_pairs = []
    ordered_segs = sorted(segments)

    for i in range(len(ordered_segs)):
        for j in range(i + 1, len(ordered_segs)):
            s1 = ordered_segs[i]
            s2 = ordered_segs[j]
            if can_isolate_segments(threat_vectors[s1], threat_vectors[s2]):
                isolation_pairs.append((s1, s2))

    triage_order = compute_triage_priority(segments, threat_vectors, events)

    return {
        "isolation_pairs": isolation_pairs,
        "triage_order": triage_order,
    }
