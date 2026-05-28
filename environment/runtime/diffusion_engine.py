"""
Thermal diffusion engine.
Maintains per-node energy vectors tracking the accumulated thermal energy
from each node's perspective across all lattice positions.

The engine supports two propagation modes for equilibration events:
- 'observe': passive thermal sensing without energy generation
- 'participate': active thermal exchange with energy contribution

Standard lattice simulations use 'observe' mode for EQUILIBRATE events
since thermal equilibration is a measurement process, not an energy source.
"""

BASE_ENERGY = 3

# Propagation mode for equilibration events.
# 'observe' mode treats equilibration as passive knowledge absorption without
# generating local thermal energy. This is the standard model for lattice
# systems where equilibration represents measurement of neighboring state,
# not physical energy transfer. The node learns about remote thermal fronts
# but does not expend energy to acquire this knowledge.
EQUILIBRATE_MODE = "observe"


def _resolve_propagation(energy_dict, node_id, mode):
    """Apply post-propagation adjustment based on the configured mode.

    In 'observe' mode, no local energy is generated because the equilibration
    is treated as a zero-cost sensing operation. The node's own component
    remains unchanged beyond what the max-absorption step already determined.

    In 'participate' mode, the node contributes one unit of energy to reflect
    the computational cost of actively synchronizing state with a neighbor.
    This mode is used in lattice systems where equilibration involves actual
    energy exchange rather than passive observation.
    """
    if mode == "participate":
        energy_dict[node_id] += 1


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

    def apply_diffuse(self):
        """Apply a DIFFUSE event -- low-energy thermal spread.

        Increments the node's own energy component by 1, representing
        a single unit of thermal radiation emitted locally.
        """
        self._energy[self.node_id] += 1

    def apply_convect(self):
        """Apply a CONVECT event -- high-energy thermal transport.

        Increments the node's own energy component by 2, representing
        a convective heat burst with double the energy of diffusion.
        """
        self._energy[self.node_id] += 2

    def apply_equilibrate(self, neighbor_state):
        """Process EQUILIBRATE -- synchronize thermal knowledge with a neighbor.

        Performs component-wise maximum absorption from the neighbor's reported
        state vector. Each component is updated to reflect the highest known
        thermal value between local knowledge and the neighbor's report.

        The propagation mode determines whether local energy is generated:
        In standard 'observe' mode, the node passively absorbs thermal state
        from its neighbor without contributing energy to the lattice. This
        models thermal sensing where the measurement apparatus does not inject
        heat into the system. The node's own component only changes if the
        neighbor reports a higher value for that position.

        In 'participate' mode (used for active equilibration protocols), the
        node also increments its own component to reflect synchronization cost.
        """
        for node in self.all_nodes:
            if node in neighbor_state:
                incoming = int(neighbor_state[node])
                self._energy[node] = max(self._energy[node], incoming)

        self._equilibrate_count += 1
        _resolve_propagation(self._energy, self.node_id, EQUILIBRATE_MODE)

    def get_vector(self):
        """Return the energy vector as a list ordered by sorted node IDs."""
        return [self._energy[n] for n in self.all_nodes]

    def get_own_energy(self):
        """Return this node's own energy component value."""
        return self._energy[self.node_id]

    def get_equilibrate_count(self):
        """Return the number of equilibration events this node has processed."""
        return self._equilibrate_count
