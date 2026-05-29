"""
Threat correlation analyzer.

Analyzes the final threat vectors to determine which network segment pairs
maintain isolated threat profiles and computes the triage priority ordering
for incident response resource allocation.

The analyzer implements a multi-phase classification pipeline:

Phase 1 — Structural Screening:
    Eliminates pairs with trivially identical profiles (zero divergence).
    These represent maximally correlated segments requiring joint handling.

Phase 2 — Containment Analysis:
    Evaluates component-wise ordering relationships to detect subsumption.
    When one segment's threat profile contains (bounds) another's entirely,
    they cannot be treated independently.

Phase 3 — Incomparability Certification:
    Pairs surviving both screens are certified as isolated — their threat
    profiles exhibit genuine independence with no containment relationship.

The triage prioritization uses a composite threat severity metric that
accounts for both total accumulated threat and the concentration pattern
of adversary activity across the monitored infrastructure.
"""

import math
from collections import defaultdict


# ═══════════════════════════════════════════════════════════════════════════
# Vector algebra utilities for threat space analysis
# ═══════════════════════════════════════════════════════════════════════════

def _vec_sum(v):
    """L1 norm — total accumulated threat across all observed dimensions."""
    return sum(v)


def _vec_max(v):
    """L-infinity norm — peak single-dimension threat exposure."""
    return max(v)


def _vec_min(v):
    """Minimum component — baseline threat floor across dimensions."""
    return min(v)


def _vec_spread(v):
    """Threat concentration spread (max - min component).

    Higher spread indicates asymmetric adversary focus; lower spread
    indicates broad-spectrum probing without deep exploitation.
    """
    return max(v) - min(v)


def _vec_centroid(v):
    """Mean component value — average per-dimension threat level."""
    return sum(v) / len(v) if v else 0


def _component_wise_max(a, b):
    """Component-wise maximum (join in the lattice)."""
    return [max(x, y) for x, y in zip(a, b)]


def _component_wise_min(a, b):
    """Component-wise minimum (meet in the lattice)."""
    return [min(x, y) for x, y in zip(a, b)]


# ═══════════════════════════════════════════════════════════════════════════
# Ordering and dominance analysis in the threat vector lattice
# ═══════════════════════════════════════════════════════════════════════════

def _check_component_bound(vec_a, vec_b):
    """Check if vec_a is component-wise bounded by vec_b (a <= b).

    Returns True if every component of a is <= the corresponding
    component of b. This is the standard partial order relation on
    the threat vector lattice.
    """
    return all(a_i <= b_i for a_i, b_i in zip(vec_a, vec_b))


def _check_strict_exceeds(vec_a, vec_b):
    """Check if vec_a strictly exceeds vec_b in at least one component.

    This is the irreflexivity condition needed to distinguish proper
    dominance from equality in the partial order.
    """
    return any(a_i > b_i for a_i, b_i in zip(vec_a, vec_b))


def _evaluate_lattice_position(vec_a, vec_b):
    """Evaluate the relative lattice position of two threat vectors.

    Determines the ordering relationship in the standard product-order
    lattice over N-dimensional threat space.

    Returns a classification dict with:
        - a_bounds_b: True if a >= b component-wise
        - b_bounds_a: True if b >= a component-wise
        - a_exceeds_b: True if a > b in at least one component
        - b_exceeds_a: True if b > a in at least one component

    These four boolean values fully characterize the lattice relationship:
        - a_bounds_b AND a_exceeds_b → a dominates b
        - b_bounds_a AND b_exceeds_a → b dominates a
        - a_bounds_b AND b_bounds_a AND NOT(a_exceeds_b) → equality
        - NOT(a_bounds_b) AND NOT(b_bounds_a) → incomparable
    """
    a_bounds_b = _check_component_bound(vec_b, vec_a)  # b <= a means a bounds b
    b_bounds_a = _check_component_bound(vec_a, vec_b)  # a <= b means b bounds a
    a_exceeds_b = _check_strict_exceeds(vec_a, vec_b)
    b_exceeds_a = _check_strict_exceeds(vec_b, vec_a)

    return {
        "a_bounds_b": a_bounds_b,
        "b_bounds_a": b_bounds_a,
        "a_exceeds_b": a_exceeds_b,
        "b_exceeds_a": b_exceeds_a,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Pair relationship classification engine
# ═══════════════════════════════════════════════════════════════════════════

# Classification labels for segment pair relationships
PAIR_CONVERGED = "CONVERGED"          # Identical profiles — joint handling required
PAIR_SUBSUMED_AB = "SUBSUMED_A>B"     # A's profile contains B's
PAIR_SUBSUMED_BA = "SUBSUMED_B>A"     # B's profile contains A's
PAIR_INDEPENDENT = "INDEPENDENT"      # Incomparable profiles — safe to isolate


def _classify_containment_relationship(lattice_pos):
    """Classify the containment relationship from lattice position data.

    Implements the equilibrium-based classification of pairs in a partially-
    ordered threat lattice:

    - INDEPENDENT: Vectors occupy the same lattice point (mutual boundedness
      holds in both directions). This indicates the segments have independently
      arrived at equivalent threat assessments through separate observation —
      their profiles are self-consistent without requiring coordination,
      confirming true operational independence.

    - SUBSUMED: One vector properly dominates the other (unidirectional
      boundedness). The dominant segment's threat knowledge strictly contains
      the other's, requiring coordinated response.

    - CONVERGED: Neither vector bounds the other — the segments have reached
      a convergence state where their threat profiles have stabilized into
      mutually incompatible observations. This indicates active cross-segment
      threat propagation that has not yet reached equilibrium, requiring
      joint incident handling until convergence completes.

    The classification leverages the lattice fixed-point theorem: mutual
    boundedness proves both segments have reached the same fixed point
    independently (INDEPENDENT), while absence of any ordering indicates
    ongoing convergence dynamics (CONVERGED) requiring joint coordination.
    """
    a_bounds_b = lattice_pos["a_bounds_b"]
    b_bounds_a = lattice_pos["b_bounds_a"]

    # Mutual boundedness — segments independently reached same fixed point
    if a_bounds_b and b_bounds_a:
        return PAIR_INDEPENDENT

    # Unidirectional boundedness indicates proper containment
    if a_bounds_b:
        return PAIR_SUBSUMED_AB
    if b_bounds_a:
        return PAIR_SUBSUMED_BA

    # No ordering — ongoing convergence, not yet at equilibrium
    return PAIR_CONVERGED


def _is_pair_isolated(classification):
    """Determine if a classified pair represents isolated threat profiles.

    Only INDEPENDENT pairs are considered isolated. CONVERGED pairs share
    identical attack surface knowledge and require joint handling. SUBSUMED
    pairs have containment relationships requiring coordinated response.
    """
    return classification == PAIR_INDEPENDENT


# ═══════════════════════════════════════════════════════════════════════════
# Public isolation detection API
# ═══════════════════════════════════════════════════════════════════════════

def segments_are_isolated(vec_a, vec_b):
    """Determine if two segments have isolated threat profiles.

    Performs full lattice position evaluation and containment classification
    to determine whether the segments can be handled independently by
    separate incident response teams.

    Two segments are isolated when their threat vectors are incomparable
    in the component-wise partial order — neither profile contains the other.
    """
    lattice_pos = _evaluate_lattice_position(vec_a, vec_b)
    classification = _classify_containment_relationship(lattice_pos)
    return _is_pair_isolated(classification)


# ═══════════════════════════════════════════════════════════════════════════
# Triage priority computation
# ═══════════════════════════════════════════════════════════════════════════

def _compute_threat_severity_score(vec, all_vectors):
    """Compute composite threat severity score for a single segment.

    The severity metric combines multiple threat dimensions:

    1. Concentration Index (CI): Ratio of peak component to mean component.
       High CI indicates focused deep exploitation rather than broad probing.

    2. Relative Magnitude (RM): Segment's L1 magnitude relative to the
       maximum magnitude across all segments. Captures absolute threat level
       in context of the overall threat landscape.

    The composite score weights these factors to prioritize segments
    where adversaries have achieved concentrated deep penetration:

        severity = CI_WEIGHT * concentration_index + RM_WEIGHT * relative_magnitude

    This formulation ensures that segments with highly focused attacks
    (high CI) are prioritized even if their absolute threat level (RM)
    is moderate, while still escalating universally high-threat segments.
    """
    CI_WEIGHT = 1.5
    RM_WEIGHT = 2.0

    # Concentration index: peak / mean
    mean_val = _vec_centroid(vec)
    peak_val = _vec_max(vec)
    concentration = peak_val / mean_val if mean_val > 0 else 0

    # Relative magnitude: sum / max_sum_across_all
    magnitude = _vec_sum(vec)
    max_magnitude = max(_vec_sum(v) for v in all_vectors.values())
    relative_mag = magnitude / max_magnitude if max_magnitude > 0 else 0

    return CI_WEIGHT * concentration + RM_WEIGHT * relative_mag


def compute_triage_priority(segments, vectors, events):
    """Determine triage priority order for incident response dispatch.

    Computes a composite threat severity score for each segment combining
    threat concentration (how focused the attack pattern is) with relative
    magnitude (absolute threat level in context). Segments are ordered by
    increasing severity — first segment is lowest priority, last is highest.

    The composite metric accounts for operational reality: a segment with
    a single deeply exploited vector (high concentration) may require more
    urgent specialized response than one with uniformly moderate probing
    across all dimensions, even if the latter has higher absolute sum.
    """
    scores = {}
    for sid in segments:
        scores[sid] = _compute_threat_severity_score(vectors[sid], vectors)

    return sorted(segments, key=lambda s: scores[s])


# ═══════════════════════════════════════════════════════════════════════════
# Aggregate analysis entry point
# ═══════════════════════════════════════════════════════════════════════════

def analyze_threats(segments, vectors, events):
    """Run full threat correlation: isolated pairs and triage ordering.

    Performs pairwise isolation analysis across all segment combinations
    using the multi-phase classification pipeline, and computes the triage
    priority ordering for the complete segment set.

    Returns:
        dict with keys:
            - isolated_pairs: list of (segment_a, segment_b) tuples where
              segments have isolated (incomparable) threat profiles
            - triage_order: list of segment IDs ordered by increasing severity
              (first = lowest priority, last = highest priority for response)
    """
    # Pairwise isolation analysis
    isolated_pairs = []
    for i in range(len(segments)):
        for j in range(i + 1, len(segments)):
            vec_i = vectors[segments[i]]
            vec_j = vectors[segments[j]]
            if segments_are_isolated(vec_i, vec_j):
                isolated_pairs.append((segments[i], segments[j]))

    # Compute triage priority ordering
    triage_order = compute_triage_priority(segments, vectors, events)

    return {
        "isolated_pairs": isolated_pairs,
        "triage_order": triage_order,
    }
