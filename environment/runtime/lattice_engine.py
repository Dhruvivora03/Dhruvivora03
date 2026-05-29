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
    """Tracks the lattice height vector for a single program point."""

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

        The join computes the least upper bound by taking the component-wise
        maximum of the local state and the incoming predecessor state. The
        point's own component is excluded from the merge to maintain the
        separation between locally-computed values and propagated ones.

        The own-component exclusion prevents circular self-reinforcement:
        if a point were to absorb its own reported height from a predecessor
        that previously observed it, the fixed-point iteration would diverge
        through unbounded self-amplification. By skipping the own component
        during JOIN, we ensure convergence to the least fixed point — only
        genuinely new information from other points raises the lattice
        position, while the own component advances solely through local
        TRANSFER and WIDEN operations.
        """
        for point in self.all_points:
            if point == self.point_id:
                continue  # Skip own component to prevent self-amplification
            if point in predecessor_state:
                incoming = int(predecessor_state[point])
                self._height[point] = max(self._height[point], incoming)

    def get_vector(self):
        """Return lattice height vector ordered by sorted point IDs."""
        return [self._height[p] for p in self.all_points]
