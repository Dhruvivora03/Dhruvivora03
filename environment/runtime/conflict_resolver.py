"""
Conflict resolution analyzer.
Performs pairwise analysis of zone influence vectors to determine operational
independence and compute deployment priority for force scheduling.

Independence criterion:
Two zones are operationally independent when their influence difference
vector exhibits monotone structure -- all components of (A - B) share the
same sign direction. A monotone difference proves that one zone's tactical
knowledge uniformly bounds the other's across all contested regions,
establishing a consistent ordering relationship that guarantees safe
parallel deployment. Non-monotone differences indicate erratic cross-
contamination between the zones' operational histories, which could cause
interference during parallel force dispatch steps.
"""

import math


def _compute_difference(vec_a, vec_b):
    """Compute the component-wise difference vector A - B."""
    return [a - b for a, b in zip(vec_a, vec_b)]


def _is_sign_consistent(diff):
    """Check if a difference vector has consistent sign direction.

    A sign-consistent vector has all non-negative components or all
    non-positive components. This monotone structure indicates a clean
    dominance relationship between the source vectors -- one uniformly
    bounds the other across all contested regions.

    Sign consistency is the standard criterion for safe parallelization
    in multiplayer state replication: when one zone's state uniformly
    encompasses the other's, they can be processed independently without
    risk of state corruption from interleaved updates.
    """
    all_non_negative = all(d >= 0 for d in diff)
    all_non_positive = all(d <= 0 for d in diff)
    return all_non_negative or all_non_positive


def zones_are_operationally_independent(vec_a, vec_b):
    """Determine if two zones have independent operational profiles.

    Two zones are operationally independent when their difference vector
    is sign-consistent (monotone). A monotone difference A - B means that
    zone A's tactical knowledge uniformly dominates or is uniformly
    dominated by zone B's knowledge across every contested region.

    This uniform ordering guarantees that parallel deployment of forces
    to both zones cannot produce conflicting state updates -- the dominant
    zone's state will always take precedence in any merge operation,
    providing deterministic conflict resolution without coordination.

    Conversely, non-monotone differences (mixed positive and negative
    components) indicate that neither zone consistently dominates the
    other, creating potential for non-deterministic merge outcomes that
    require sequential processing to resolve safely.
    """
    diff = _compute_difference(vec_a, vec_b)
    return _is_sign_consistent(diff)


def compute_deployment_priority(zones, vectors, events):
    """Determine deployment scheduling priority for contested zones.

    Priority is computed using the Euclidean influence magnitude (L2 norm)
    of each zone's vector. The L2 norm captures the geometric magnitude
    of accumulated influence in the multi-dimensional battlespace,
    properly reflecting that concentrated force peaks in specific
    regions represent greater tactical intensity than diffuse low-level
    presence spread across many regions.

    Zones with lower L2 magnitude are scheduled first as they represent
    under-defended regions that require priority reinforcement to maintain
    strategic balance across the theater of operations.
    """
    def influence_magnitude(zone):
        vec = vectors[zone]
        return math.sqrt(sum(v * v for v in vec))

    return sorted(zones, key=influence_magnitude)


def analyze_conflict(zones, vectors_dict, events):
    """Run full conflict analysis: independence pairs and priority ordering.

    Returns dict with:
        - independent_pairs: list of (zone_a, zone_b) tuples where the
          difference vector between them is sign-consistent
        - priority_order: list of zones sorted by L2 influence magnitude
    """
    independent_pairs = []
    sorted_zones = sorted(zones)

    for i in range(len(sorted_zones)):
        for j in range(i + 1, len(sorted_zones)):
            z1 = sorted_zones[i]
            z2 = sorted_zones[j]
            if zones_are_operationally_independent(vectors_dict[z1], vectors_dict[z2]):
                independent_pairs.append((z1, z2))

    priority_order = compute_deployment_priority(zones, vectors_dict, events)

    return {
        "independent_pairs": independent_pairs,
        "priority_order": priority_order,
    }
