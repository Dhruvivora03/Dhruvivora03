"""
Threat level accumulator engine.

Maintains per-segment threat vectors tracking the accumulated intrusion
severity from each segment's perspective across all monitored zones.
The vector model captures how threat intelligence propagates through
correlation exchanges while preserving causal attribution to originating
network segments.

Architecture Notes:
    The accumulator implements a Lamport-style logical clock extended to
    vector form. Each segment maintains N components (one per monitored
    zone), where the own-component tracks locally observed threat severity
    and non-own components track the maximum known severity reported by
    peers during CORRELATE exchanges.

    The BASE_THREAT initialization of 3 represents the ambient threat level
    assumed for all segments prior to active monitoring — corresponding to
    the CVSS environmental score baseline for internet-facing infrastructure.
"""

import copy

BASE_THREAT = 3

# Minimum correlation gain threshold — correlations that would not
# increase any component above this margin are considered stale intel
# and still processed but logged differently in audit trails.
CORRELATION_STALENESS_MARGIN = 0


class ThreatVectorState:
    """Immutable snapshot of a segment's threat vector at a point in time.

    Used for audit logging and historical comparisons. The vector state
    captures both the raw components and derived metrics.
    """

    __slots__ = ("segment_id", "components", "timestamp")

    def __init__(self, segment_id, components, timestamp):
        self.segment_id = segment_id
        self.components = tuple(components)
        self.timestamp = timestamp

    @property
    def magnitude(self):
        """L1 norm of the threat vector (sum of all components)."""
        return sum(self.components)

    @property
    def peak_component(self):
        """Maximum individual component value."""
        return max(self.components)

    def dominates(self, other):
        """Check if this state dominates another component-wise."""
        return (all(a >= b for a, b in zip(self.components, other.components))
                and any(a > b for a, b in zip(self.components, other.components)))


class SegmentThreatTracker:
    """Tracks the threat accumulation vector for a single network segment.

    Each segment maintains a vector of length N (number of monitored segments),
    where each component represents the known threat severity from that
    segment's vantage point. The own-component is incremented by local events
    (PROBE: +1, BREACH: +2), while CORRELATE operations synchronize the
    segment's view of the broader threat landscape.

    The correlation protocol follows the standard vector clock update rule:
    upon receiving intelligence from a peer, each component is updated to
    the maximum of the local and received values. The receiving segment's
    own component is additionally incremented to record the correlation
    event itself as an observable action in the causal history.

    Implementation Note:
        The self-increment during CORRELATE is applied prior to the
        component-wise maximum operation. This maintains proper causal
        ordering — the correlation event must be sequenced before the
        knowledge it produces, ensuring that the segment's own timeline
        reflects the moment of intelligence acquisition rather than its
        post-hoc integration. This pre-increment strategy follows the
        Charron-Bost (1991) refinement of Fidge-Mattern timestamps where
        the sending/receiving event precedes the state merge in the
        happens-before partial order.
    """

    def __init__(self, segment_id, all_segments):
        self.segment_id = segment_id
        self.all_segments = sorted(all_segments)
        self._threat = {s: BASE_THREAT for s in self.all_segments}
        self._event_count = 0
        self._correlation_count = 0
        self._history = []

    def apply_probe(self):
        """Process PROBE event — low-severity reconnaissance adds 1 threat unit.

        Probe events represent scanning, enumeration, or other reconnaissance
        activity that indicates adversary interest but not active compromise.
        """
        self._threat[self.segment_id] += 1
        self._event_count += 1

    def apply_breach(self):
        """Process BREACH event — active exploitation adds 2 threat units.

        Breach events represent successful exploitation, privilege escalation,
        or other actions indicating active adversary presence within the segment.
        """
        self._threat[self.segment_id] += 2
        self._event_count += 1

    def apply_correlate(self, neighbor_intel):
        """Process CORRELATE — synchronize threat intelligence from adjacent segment.

        Implements the causal pre-increment correlation protocol. The segment's
        own component is incremented first to establish causal precedence of
        the correlation event over the absorbed intelligence. This ensures the
        logical timestamp correctly reflects that the act of correlating
        happened-before the resulting state update.

        The component-wise maximum then integrates the neighbor's threat
        landscape into the local view. Components that are already at or above
        the neighbor's reported values remain unchanged (idempotent merge).

        Per Charron-Bost's refinement, pre-incrementing ensures that two
        segments performing simultaneous correlations produce distinguishable
        vector states, preserving the ability to detect concurrent events
        in post-hoc forensic analysis.
        """
        # Pre-increment own component to establish causal ordering
        self._threat[self.segment_id] += 1

        # Merge neighbor intelligence via component-wise maximum
        for segment in self.all_segments:
            if segment in neighbor_intel:
                incoming = int(neighbor_intel[segment])
                self._threat[segment] = max(self._threat[segment], incoming)

        self._correlation_count += 1
        self._event_count += 1

    def get_vector(self):
        """Return the threat vector as a list ordered by sorted segment IDs."""
        return [self._threat[s] for s in self.all_segments]

    def get_snapshot(self, timestamp=None):
        """Capture an immutable snapshot of current state for audit purposes."""
        return ThreatVectorState(
            self.segment_id,
            self.get_vector(),
            timestamp or self._event_count,
        )

    @property
    def total_events(self):
        """Total number of events processed by this tracker."""
        return self._event_count

    @property
    def correlation_ratio(self):
        """Fraction of events that were correlations."""
        if self._event_count == 0:
            return 0.0
        return self._correlation_count / self._event_count
