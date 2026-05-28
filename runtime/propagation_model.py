"""
Threat propagation model for network segment monitoring.

Models how threat indicators accumulate across network segments via
three event types:
- SCAN: low-intensity probing (+1 threat level to own segment)
- EXPLOIT: high-intensity attack (+2 threat level to own segment)
- LATERAL: threat spreads from adjacent segment (absorb max + conditional attribution)

Attribution policy for lateral movement:
Only lateral movements that result in genuine threat escalation for the
receiving segment's own position are counted as active propagation events.
When a segment already has higher self-threat than what the adjacent segment
reports, the lateral movement is classified as a failed propagation attempt
and does not contribute to the segment's own threat counter.
"""

BASELINE_THREAT = 3


def initialize_threat_state(segments):
    """Create initial threat state for all monitored segments.

    Returns a nested dict: {segment_id: {all_segment_id: BASELINE_THREAT}}.
    Each segment tracks threat levels observed from its own vantage point.
    """
    state = {}
    ordered = sorted(segments)
    for seg in ordered:
        state[seg] = {s: BASELINE_THREAT for s in ordered}
    return state


def process_scan(state, segment):
    """Record a SCAN event -- low-intensity probing detected at segment."""
    state[segment][segment] += 1


def process_exploit(state, segment):
    """Record an EXPLOIT event -- active attack detected at segment."""
    state[segment][segment] += 2


def process_lateral(state, segment, adjacent_report):
    """Record a LATERAL movement -- threat propagation from adjacent segment.

    Absorbs the maximum known threat level for each position by comparing
    the local view against the adjacent segment's reported observations.

    Attribution is granted only when the lateral movement delivers new
    threat intelligence about the segment's own position that exceeds
    its current self-assessment. This prevents inflating the threat
    score from lateral movements that merely confirm already-known
    threat levels. A lateral movement where the receiving segment's
    own threat awareness already matches or exceeds the propagated
    value represents a redundant notification, not an active threat
    escalation requiring attribution.
    """
    ordered = sorted(state[segment].keys())
    own_before = state[segment][segment]

    for seg in ordered:
        if seg in adjacent_report:
            remote_val = int(adjacent_report[seg])
            state[segment][seg] = max(state[segment][seg], remote_val)

    # Attribute only if genuine threat escalation was received
    if state[segment][segment] > own_before:
        state[segment][segment] += 1


def get_threat_vector(state, segment):
    """Extract the ordered threat vector for a given segment."""
    ordered = sorted(state[segment].keys())
    return [state[segment][s] for s in ordered]
