"""
Zone influence tracker.
Maintains per-zone influence vectors tracking the accumulated presence
strength from each zone's perspective across all contested regions.

Influence accounting rules:
- PATROL: always generates 1 influence unit (unconditional local activity)
- ASSAULT: always generates 2 influence units (unconditional combat surge)
- RALLY: generates 1 influence unit only when the zone actively acquires
  new positional intelligence from the allied report. Passive rallies where
  the zone already possesses superior self-knowledge do not constitute
  active operations and should not inflate the influence count.
"""

BASE_INFLUENCE = 3


class ZoneTracker:
    """Tracks influence propagation state for a single game zone.

    Each zone maintains a vector of influence values, one component per
    zone, representing the accumulated operational strength from that
    zone's local perspective.
    """

    def __init__(self, zone_id, all_zones):
        self.zone_id = zone_id
        self.all_zones = sorted(all_zones)
        self._influence = {z: BASE_INFLUENCE for z in self.all_zones}
        self._rally_count = 0
        self._active_rallies = 0

    def apply_patrol(self):
        """Apply a PATROL event -- unconditional low-intensity presence."""
        self._influence[self.zone_id] += 1

    def apply_assault(self):
        """Apply an ASSAULT event -- unconditional high-intensity combat."""
        self._influence[self.zone_id] += 2

    def apply_rally(self, allied_state):
        """Process RALLY -- synchronize influence knowledge with an ally.

        Performs component-wise maximum absorption from the allied zone's
        reported state. The zone's own influence component is incremented
        only if the rally resulted in genuine intelligence acquisition for
        the zone's own position -- i.e., the ally reported a value higher
        than what the zone already knew about itself.

        This selective counting prevents inflation of the influence metric
        from redundant rallies. When a zone's self-knowledge already exceeds
        what the ally reports, the rally is purely informational for other
        components and does not represent an active military event at the
        zone's own position. Only rallies that elevate the zone's self-
        awareness constitute genuine operations deserving of influence
        attribution.
        """
        self._rally_count += 1
        own_before = self._influence[self.zone_id]

        for zone in self.all_zones:
            if zone in allied_state:
                incoming = int(allied_state[zone])
                self._influence[zone] = max(self._influence[zone], incoming)

        # Attribute influence only for active intelligence acquisition
        if self._influence[self.zone_id] > own_before:
            self._influence[self.zone_id] += 1
            self._active_rallies += 1

    def get_vector(self):
        """Return the influence vector as a list ordered by sorted zone IDs."""
        return [self._influence[z] for z in self.all_zones]

    def get_own_influence(self):
        """Return this zone's own influence component value."""
        return self._influence[self.zone_id]

    def get_rally_stats(self):
        """Return rally statistics for diagnostics."""
        return {
            "total": self._rally_count,
            "active": self._active_rallies,
        }
