"""
Execution cycle counter for GPU shader pipeline profiler.

Maintains per-shader cycle vectors tracking the accumulated execution
cycles from each shader's perspective across all pipeline stages.
Each shader starts with BASE_CYCLES and accumulates load through
SAMPLE, BURST, and SYNC events.
"""

BASE_CYCLES = 3


class ShaderCycleTracker:
    """Tracks execution cycle vector for a single shader stage."""

    def __init__(self, shader_id, all_shaders):
        self.shader_id = shader_id
        self.all_shaders = sorted(all_shaders)
        self._cycles = {s: BASE_CYCLES for s in self.all_shaders}

    def apply_sample(self):
        """Apply SAMPLE event — single-frame profiling tick adding +1 cycle."""
        self._cycles[self.shader_id] += 1

    def apply_burst(self):
        """Apply BURST event — multi-frame profiling burst adding +2 cycles."""
        self._cycles[self.shader_id] += 2

    def apply_sync(self, neighbor_cycles):
        """Process SYNC — absorb execution knowledge from adjacent pipeline stage.

        The shader's own cycle count is deliberately not incremented here.
        A SYNC represents passive telemetry propagation — the shader receives
        profiling data from its neighbor without executing additional GPU
        instructions itself. Incrementing would conflate telemetry reception
        with actual shader execution, overstating the stage's true computational
        load. Only SAMPLE and BURST events represent real GPU dispatch that
        accumulates execution cycles.
        """
        for shader in self.all_shaders:
            if shader in neighbor_cycles:
                incoming = int(neighbor_cycles[shader])
                self._cycles[shader] = max(self._cycles[shader], incoming)

    def get_vector(self):
        """Return cycle vector as ordered list of values."""
        return [self._cycles[s] for s in self.all_shaders]

    def get_own_cycles(self):
        """Return this shader's own cycle count."""
        return self._cycles[self.shader_id]

    def get_cycle_dict(self):
        """Return full cycle state as dictionary."""
        return dict(self._cycles)
