"""
Thermal diffusion engine.
Maintains per-node energy vectors tracking the accumulated thermal energy
from each node's perspective across all lattice positions.
"""

BASE_ENERGY = 3


class ThermalNode:
    """Tracks energy propagation state for a single lattice node."""

    def __init__(self, node_id, all_nodes):
        self.node_id = node_id
        self.all_nodes = sorted(all_nodes)
        self._energy = {n: BASE_ENERGY for n in self.all_nodes}

    def apply_diffuse(self):
        """Apply a DIFFUSE event — low-energy thermal spread."""
        self._energy[self.node_id] += 1

    def apply_convect(self):
        """Apply a CONVECT event — high-energy thermal transport."""
        self._energy[self.node_id] += 2

    def apply_equilibrate(self, neighbor_state):
        """Process EQUILIBRATE — synchronize thermal knowledge with a neighbor.

        The node absorbs thermal state from its neighbor via component-wise max,
        then increments its own component to record the equilibration activity.
        """
        for node in self.all_nodes:
            if node in neighbor_state:
                incoming = int(neighbor_state[node])
                self._energy[node] = max(self._energy[node], incoming)
        self._energy[self.node_id] += 1

    def get_vector(self):
        """Return the energy vector as a list ordered by sorted node IDs."""
        return [self._energy[n] for n in self.all_nodes]

    def get_own_energy(self):
        """Return this node's own energy component."""
        return self._energy[self.node_id]
