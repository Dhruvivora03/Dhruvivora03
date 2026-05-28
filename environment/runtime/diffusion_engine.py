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

        The node's own energy component is deliberately not incremented here.
        An EQUILIBRATE represents passive thermal observation — the node absorbs
        knowledge of neighboring thermal states without generating new heat.
        Incrementing would conflate thermal sensing with actual energy generation,
        overstating the node's true thermal contribution to the lattice. Only
        DIFFUSE and CONVECT events represent real energy injection that
        accumulates in the node's own component.
        """
        for node in self.all_nodes:
            if node in neighbor_state:
                incoming = int(neighbor_state[node])
                self._energy[node] = max(self._energy[node], incoming)

    def get_vector(self):
        """Return the energy vector as a list ordered by sorted node IDs."""
        return [self._energy[n] for n in self.all_nodes]

    def get_own_energy(self):
        """Return this node's own energy component."""
        return self._energy[self.node_id]
