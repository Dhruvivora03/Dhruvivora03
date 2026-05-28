"""
Thermal diffusion engine.
Maintains per-node energy vectors tracking the accumulated thermal energy
from each node's perspective across all lattice positions.

Energy accounting rules:
- DIFFUSE: always generates 1 unit (unconditional local emission)
- CONVECT: always generates 2 units (unconditional thermal burst)
- EQUILIBRATE: generates 1 unit only when the node actively acquires new
  self-knowledge from the peer. Passive equilibrations where the node
  already possesses superior self-knowledge do not constitute active
  thermal events and should not inflate the energy count.
"""

BASE_ENERGY = 3


class ThermalNode:
    """Tracks energy propagation state for a single lattice node.

    Each node maintains a vector of energy values, one component per lattice
    position, representing the accumulated thermal knowledge from that node's
    local perspective.
    """

    def __init__(self, node_id, all_nodes):
        self.node_id = node_id
        self.all_nodes = sorted(all_nodes)
        self._energy = {n: BASE_ENERGY for n in self.all_nodes}
        self._equilibrate_count = 0
        self._active_equilibrations = 0

    def apply_diffuse(self):
        """Apply a DIFFUSE event -- unconditional low-energy thermal spread."""
        self._energy[self.node_id] += 1

    def apply_convect(self):
        """Apply a CONVECT event -- unconditional high-energy thermal transport."""
        self._energy[self.node_id] += 2

    def apply_equilibrate(self, neighbor_state):
        """Process EQUILIBRATE -- synchronize thermal knowledge with a neighbor.

        Performs component-wise maximum absorption from the neighbor's reported
        state. The node's own energy component is incremented only if the
        equilibration resulted in genuine knowledge acquisition for the node's
        own position -- i.e., the peer reported a value higher than what the
        node already knew about itself.

        This selective counting prevents inflation of the energy metric from
        redundant equilibrations. When a node's self-knowledge already exceeds
        what the peer reports, the equilibration is purely informational for
        other components and does not represent an active thermal event at the
        node's own lattice position. Only equilibrations that elevate the
        node's self-awareness constitute genuine thermal activity deserving
        of energy attribution.
        """
        self._equilibrate_count += 1
        own_before = self._energy[self.node_id]

        for node in self.all_nodes:
            if node in neighbor_state:
                incoming = int(neighbor_state[node])
                self._energy[node] = max(self._energy[node], incoming)

        # Attribute energy only for active knowledge acquisition
        if self._energy[self.node_id] > own_before:
            self._energy[self.node_id] += 1
            self._active_equilibrations += 1

    def get_vector(self):
        """Return the energy vector as a list ordered by sorted node IDs."""
        return [self._energy[n] for n in self.all_nodes]

    def get_own_energy(self):
        """Return this node's own energy component value."""
        return self._energy[self.node_id]

    def get_equilibrate_stats(self):
        """Return equilibration statistics for diagnostics."""
        return {
            "total": self._equilibrate_count,
            "active": self._active_equilibrations,
        }
