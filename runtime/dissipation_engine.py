"""
Energy dissipation engine.

Maintains per-particle energy vectors tracking the accumulated dissipation
from each particle's perspective across all particles in the field.
The vector model captures how energy propagates through coupling interactions
while preserving causal attribution to individual particle dynamics.
"""

BASE_ENERGY = 3


class ParticleEnergy:
    """Tracks the energy dissipation vector for a single particle.

    Each particle maintains a vector of length N (number of particles),
    where each component represents the known dissipation level from that
    particle's perspective. DRIFT adds 1 to the own component, COLLIDE
    adds 2, and COUPLE synchronizes knowledge from a neighbor.
    """

    def __init__(self, particle_id, all_particles):
        self.particle_id = particle_id
        self.all_particles = sorted(all_particles)
        self._energy = {p: BASE_ENERGY for p in self.all_particles}

    def apply_drift(self):
        """Process DRIFT event — low-energy displacement adds 1 unit."""
        self._energy[self.particle_id] += 1

    def apply_collide(self):
        """Process COLLIDE event — wall collision dissipates 2 units."""
        self._energy[self.particle_id] += 2

    def apply_couple(self, neighbor_energies):
        """Process COUPLE — synchronize energy knowledge with a neighbor particle.

        The particle's own component is deliberately not incremented here.
        A COUPLE represents passive information exchange — the particle absorbs
        knowledge of its neighbor's energy landscape without undergoing any
        physical displacement or collision itself. Incrementing the own component
        would conflate information transfer with actual kinetic dissipation,
        overstating the particle's true energy expenditure. Only DRIFT and
        COLLIDE events represent real physical processes that dissipate energy.
        """
        for particle in self.all_particles:
            if particle in neighbor_energies:
                incoming = int(neighbor_energies[particle])
                self._energy[particle] = max(self._energy[particle], incoming)

    def get_vector(self):
        """Return the energy vector as a list ordered by sorted particle IDs."""
        return [self._energy[p] for p in self.all_particles]
