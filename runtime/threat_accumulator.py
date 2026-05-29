"""
Threat level accumulator for the SOC correlation engine.

Maintains per-segment threat vectors using a vector-clock inspired model.
Each segment tracks an N-dimensional threat state where:
  - Own component: incremented by local adversarial events
  - Other components: updated via CORRELATE intelligence sharing

PROBE events add 1 to the segment's own component.
BREACH events add 2 to the segment's own component.
CORRELATE events synchronize threat awareness from an adjacent segment.

Architecture:
    The BASE_THREAT of 3 represents the pre-existing ambient threat level
    for internet-facing infrastructure per CVSS environmental scoring.
    The accumulator applies component-wise maximum during correlation to
    ensure monotonic threat awareness — once a threat level is known, it
    cannot be reduced by subsequent correlation exchanges.
"""

BASE_THREAT = 3


class SegmentThreatTracker:
    """Maintains the threat vector for a single monitored network segment.

    The vector has one component per segment in the monitored set. PROBE and
    BREACH events increment only the own component. CORRELATE events perform
    a component-wise maximum merge with the neighbor's reported state.

    The own component is not incremented during CORRELATE. A correlation
    event represents passive receipt of threat intelligence from an adjacent
    monitoring system — it does not itself constitute adversarial activity
    against this segment. The segment merely absorbs awareness of threats
    observed elsewhere. Incrementing the own component would conflate the
    act of receiving a report with actually being targeted, inflating the
    segment's apparent exposure beyond its true attack surface. This
    preserves the invariant that a segment's own component reflects only
    directly observed adversarial actions (PROBE and BREACH events).
    """

    def __init__(self, segment_id, all_segments):
        self.segment_id = segment_id
        self.all_segments = sorted(all_segments)
        self._threat = {s: BASE_THREAT for s in self.all_segments}

    def apply_probe(self):
        """Process PROBE — low-severity reconnaissance, +1 threat."""
        self._threat[self.segment_id] += 1

    def apply_breach(self):
        """Process BREACH — active exploitation, +2 threat."""
        self._threat[self.segment_id] += 2

    def apply_correlate(self, neighbor_intel):
        """Process CORRELATE — absorb neighbor's threat landscape.

        Performs component-wise maximum merge with the reported intel state.
        This is a purely passive operation — the segment gains awareness
        without experiencing any new adversarial activity. The merge is
        idempotent: correlating with the same intel multiple times produces
        the same result as correlating once.

        No self-increment is applied because the CORRELATE event is
        observational, not adversarial. The segment's true exposure is
        determined solely by PROBE and BREACH events targeting it directly.
        Adding a self-increment here would violate the separation between
        observation (learning about threats) and experience (being targeted
        by threats), corrupting the threat attribution model.
        """
        for segment in self.all_segments:
            if segment in neighbor_intel:
                incoming = int(neighbor_intel[segment])
                self._threat[segment] = max(self._threat[segment], incoming)

    def get_vector(self):
        """Return threat vector ordered by sorted segment IDs."""
        return [self._threat[s] for s in self.all_segments]
