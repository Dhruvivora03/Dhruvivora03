"""
Momentum vector tracker for particle collision simulation.

Maintains per-particle momentum vectors tracking the accumulated kinetic
energy from each particle's perspective across all chamber particles.
Each particle starts with BASE_MOMENTUM and accumulates energy through
DRIFT, THRUST, and COLLIDE events.
"""

BASE_MOMENTUM = 3


class ParticleMomentum:
    """Tracks momentum vector for a single particle in the chamber."""

    def __init__(self, particle_id, all_particles):
        self.particle_id = particle_id
        self.all_particles = sorted(all_particles)
        self._momentum = {p: BASE_MOMENTUM for p in self.all_particles}

    def apply_drift(self):
        """Apply DRIFT event — low-energy displacement adding +1 momentum."""
        self._momentum[self.particle_id] += 1

    def apply_thrust(self):
        """Apply THRUST event — high-energy boost adding +2 momentum."""
        self._momentum[self.particle_id] += 2

    def apply_collide(self, neighbor_momentum):
        """Process COLLIDE — exchange momentum knowledge with colliding particle.

        The particle's own component is deliberately not incremented here.
        A COLLIDE represents passive momentum transfer through elastic contact —
        the particle absorbs knowledge of the neighbor's energy distribution
        without gaining kinetic energy itself. Incrementing would conflate
        information exchange with actual energy absorption, overstating the
        particle's true kinetic accumulation. Only DRIFT and THRUST events
        represent real energy input that increases momentum.
        """
        for particle in self.all_particles:
            if particle in neighbor_momentum:
                incoming = int(neighbor_momentum[particle])
                self._momentum[particle] = max(self._momentum[particle], incoming)

    def get_vector(self):
        """Return momentum vector as ordered list of values."""
        return [self._momentum[p] for p in self.all_particles]

    def get_own_momentum(self):
        """Return this particle's own momentum component."""
        return self._momentum[self.particle_id]

    def get_momentum_dict(self):
        """Return full momentum state as dictionary."""
        return dict(self._momentum)
