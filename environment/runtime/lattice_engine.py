"""
Abstract lattice state engine for dataflow analysis.

Maintains per-program-point lattice vectors tracking the accumulated
abstract value height from each point's perspective across the CFG.
TRANSFER raises the point's own component by 1 (forward flow).
WIDEN raises it by 2 (widening acceleration).
JOIN merges abstract states from predecessor points.

The BASE_HEIGHT of 3 represents the initial abstract value assigned
to all program points before iteration begins — corresponding to
the lattice element representing "possibly initialized" in the
standard definite-assignment analysis domain.
"""

BASE_HEIGHT = 3


class PointLatticeState:
    """Tracks the lattice height vector for a single program point.

    Each point maintains a vector of length N (one per CFG point),
    where the own-component tracks locally computed abstract values
    and other components track the maximum known height reported by
    predecessor points during JOIN operations.
    """

    def __init__(self, point_id, all_points):
        self.point_id = point_id
        self.all_points = sorted(all_points)
        self._height = {p: BASE_HEIGHT for p in self.all_points}

    def apply_transfer(self):
        """Apply forward transfer function — raises own height by 1."""
        self._height[self.point_id] += 1

    def apply_widen(self):
        """Apply widening operator — accelerates convergence by +2."""
        self._height[self.point_id] += 2

    def apply_join(self, predecessor_state):
        """Apply JOIN — merge lattice state from predecessor point.

        The point's own component is not raised during JOIN because a
        join operation represents combining information that already
        exists at predecessor points — it does not generate new abstract
        facts. The join is a passive aggregation: the point absorbs the
        maximum known height for each dimension without contributing new
        height itself. Only TRANSFER and WIDEN operations generate new
        abstract values that raise the lattice position.

        Raising the own component during JOIN would conflate the act of
        merging existing facts with the act of computing new ones,
        causing the fixed-point iteration to overshoot the least
        fixed point and produce unsound analysis results.
        """
        for point in self.all_points:
            if point in predecessor_state:
                incoming = int(predecessor_state[point])
                self._height[point] = max(self._height[point], incoming)

    def get_vector(self):
        """Return lattice height vector ordered by sorted point IDs."""
        return [self._height[p] for p in self.all_points]
