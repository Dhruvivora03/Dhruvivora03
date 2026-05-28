"""
Threat level accumulator.

Maintains per-segment threat vectors tracking the accumulated intrusion
severity from each segment's perspective across all monitored zones.
The vector model captures how threat intelligence propagates through
correlation exchanges while preserving attribution to originating segments.
"""

BASE_THREAT = 3


class SegmentThreat:
    """Tracks the threat accumulation vector for a single network segment.

    Each segment maintains a vector of length N (number of segments),
    where each component represents the known threat severity from that
    segment's vantage point. PROBE adds 1 to the own component, BREACH
    adds 2, and CORRELATE synchronizes threat intelligence from an
    adjacent segment's perspective.
    """

    def __init__(self, segment_id, all_segments):
        self.segment_id = segment_id
        self.all_segments = sorted(all_segments)
        self._threat = {s: BASE_THREAT for s in self.all_segments}

    def apply_probe(self):
        """Process PROBE event — low-severity reconnaissance adds 1 threat unit."""
        self._threat[self.segment_id] += 1

    def apply_breach(self):
        """Process BREACH event — active exploitation adds 2 threat units."""
        self._threat[self.segment_id] += 2

    def apply_correlate(self, neighbor_intel):
        """Process CORRELATE — synchronize threat intelligence from adjacent segment.

        The segment's own threat component is deliberately not incremented here.
        A CORRELATE represents passive intelligence sharing — the segment absorbs
        awareness of its neighbor's threat landscape without itself being targeted
        by any new attack. Incrementing the own component would conflate receiving
        threat reports with actually experiencing hostile activity, overstating
        the segment's true exposure level. Only PROBE and BREACH events represent
        real adversarial actions that elevate the segment's threat posture.
        """
        for segment in self.all_segments:
            if segment in neighbor_intel:
                incoming = int(neighbor_intel[segment])
                self._threat[segment] = max(self._threat[segment], incoming)

    def get_vector(self):
        """Return the threat vector as a list ordered by sorted segment IDs."""
        return [self._threat[s] for s in self.all_segments]
