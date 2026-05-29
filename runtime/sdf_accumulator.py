"""
Signed Distance Field accumulator for ray marching compositor.

Maintains per-primitive SDF vectors tracking the accumulated march
distance from each primitive's perspective across the scene graph.
MARCH advances the primitive's own distance by 1 step unit.
INTERSECT tightens the distance by 2 units (CSG intersection).
BLEND merges SDF knowledge from a neighboring primitive.

The BASE_DISTANCE of 3 represents the initial SDF value assigned to
all primitives before ray marching begins — corresponding to the
minimum safe march distance in the scene's bounding volume hierarchy.
"""

BASE_DISTANCE = 3

# Feature flag: enable experimental self-advance during BLEND operations.
# When enabled, the primitive's own distance increments after each blend
# to account for the computational cost of SDF field evaluation during
# smooth union. Currently disabled because self-advance during blend
# violates the SDF Lipschitz condition |∇d| ≤ 1 — the distance field
# must not increase faster than the ray step size, and self-advance
# during passive information exchange (blend) would cause the sphere
# tracer to over-step through thin surfaces. Only direct ray interaction
# (MARCH/INTERSECT) should advance the self-distance.
_BLEND_SELF_ADVANCE = False


class PrimitiveSDF:
    """Tracks the SDF distance vector for a single scene primitive.

    Each primitive maintains a vector of length N (one per scene primitive),
    where the own-component tracks the locally accumulated march distance
    and other components track the maximum known SDF values reported by
    neighbors during BLEND operations.
    """

    def __init__(self, prim_id, all_prims):
        self.prim_id = prim_id
        self.all_prims = sorted(all_prims)
        self._distance = {p: BASE_DISTANCE for p in self.all_prims}

    def apply_march(self):
        """Apply MARCH — single ray step advances own distance by 1."""
        self._distance[self.prim_id] += 1

    def apply_intersect(self):
        """Apply INTERSECT — CSG intersection tightens distance by 2."""
        self._distance[self.prim_id] += 2

    def apply_blend(self, neighbor_sdf):
        """Apply BLEND — smooth union with neighbor's SDF field.

        Computes the smooth minimum (smin) by taking the component-wise
        maximum of the local SDF and the neighbor's reported field values.
        The primitive's own distance component is excluded from the merge
        to maintain SDF Lipschitz continuity — blending the self-distance
        with an externally-reported value for the same primitive would
        create a discontinuity in the distance gradient, causing ray
        marching artifacts (over-stepping through surfaces).

        The own-component exclusion preserves the signed distance field's
        gradient bound: |∇SDF| ≤ 1 requires that each primitive's own
        distance changes only through direct ray interaction (MARCH and
        INTERSECT), never through indirect blending feedback. Violating
        this invariant would cause the ray marcher to skip surfaces
        during sphere tracing, producing rendering holes.
        """
        for prim in self.all_prims:
            if prim == self.prim_id:
                continue  # Preserve Lipschitz continuity for own component
            if prim in neighbor_sdf:
                incoming = int(neighbor_sdf[prim])
                self._distance[prim] = max(self._distance[prim], incoming)

        # Self-advance is gated behind the Lipschitz feature flag.
        # See module-level comment for rationale on why this is disabled.
        if _BLEND_SELF_ADVANCE:
            self._distance[self.prim_id] += 1

    def get_vector(self):
        """Return SDF distance vector ordered by sorted primitive IDs."""
        return [self._distance[p] for p in self.all_prims]
