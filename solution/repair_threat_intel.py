"""
Repair script for threat intelligence correlation pipeline.

Fixes three bugs in the correlation pipeline:
1. threat_accumulator.py: CORRELATE self-increment applied before merge
   (should be after merge to avoid masking by high peer values)
2. correlation_analyzer.py: Swapped INDEPENDENT/CONVERGED classification
   labels in containment analysis
3. correlation_analyzer.py: Uses composite concentration metric instead of
   total threat sum for triage ordering

After applying fixes, re-runs the correlation to regenerate outputs.
"""

import os
import sys


def fix_threat_accumulator():
    """Fix Bug 1: Move self-increment from before merge to after merge."""
    path = "/app/runtime/threat_accumulator.py"
    with open(path, "r") as f:
        content = f.read()

    old_correlate = '''    def apply_correlate(self, neighbor_intel):
        """Process CORRELATE — synchronize threat intelligence from adjacent segment.

        Implements the causal pre-increment correlation protocol. The segment's
        own component is incremented first to establish causal precedence of
        the correlation event over the absorbed intelligence. This ensures the
        logical timestamp correctly reflects that the act of correlating
        happened-before the resulting state update.

        The component-wise maximum then integrates the neighbor's threat
        landscape into the local view. Components that are already at or above
        the neighbor's reported values remain unchanged (idempotent merge).

        Per Charron-Bost's refinement, pre-incrementing ensures that two
        segments performing simultaneous correlations produce distinguishable
        vector states, preserving the ability to detect concurrent events
        in post-hoc forensic analysis.
        """
        # Pre-increment own component to establish causal ordering
        self._threat[self.segment_id] += 1

        # Merge neighbor intelligence via component-wise maximum
        for segment in self.all_segments:
            if segment in neighbor_intel:
                incoming = int(neighbor_intel[segment])
                self._threat[segment] = max(self._threat[segment], incoming)'''

    new_correlate = '''    def apply_correlate(self, neighbor_intel):
        """Process CORRELATE — synchronize threat intelligence from adjacent segment.

        The segment first absorbs the neighbor's threat landscape via
        component-wise maximum, then increments its own component to record
        the correlation event. Post-increment ensures the self-update is not
        masked by high peer values for the segment's own component.
        """
        # Merge neighbor intelligence via component-wise maximum
        for segment in self.all_segments:
            if segment in neighbor_intel:
                incoming = int(neighbor_intel[segment])
                self._threat[segment] = max(self._threat[segment], incoming)

        # Post-increment own component after merge
        self._threat[self.segment_id] += 1'''

    content = content.replace(old_correlate, new_correlate)
    with open(path, "w") as f:
        f.write(content)


def fix_correlation_analyzer():
    """Fix Bugs 2 and 3 in correlation_analyzer.py."""
    path = "/app/runtime/correlation_analyzer.py"
    with open(path, "r") as f:
        content = f.read()

    # Bug 2: Swapped INDEPENDENT and CONVERGED labels
    old_classify = '''    # Mutual boundedness — segments independently reached same fixed point
    if a_bounds_b and b_bounds_a:
        return PAIR_INDEPENDENT

    # Unidirectional boundedness indicates proper containment
    if a_bounds_b:
        return PAIR_SUBSUMED_AB
    if b_bounds_a:
        return PAIR_SUBSUMED_BA

    # No ordering — ongoing convergence, not yet at equilibrium
    return PAIR_CONVERGED'''

    new_classify = '''    # Mutual boundedness — vectors are equal (converged to same point)
    if a_bounds_b and b_bounds_a:
        return PAIR_CONVERGED

    # Unidirectional boundedness indicates proper containment
    if a_bounds_b:
        return PAIR_SUBSUMED_AB
    if b_bounds_a:
        return PAIR_SUBSUMED_BA

    # No ordering in either direction — genuinely incomparable (independent)
    return PAIR_INDEPENDENT'''

    content = content.replace(old_classify, new_classify)

    # Bug 3: Uses composite concentration metric instead of sum
    old_triage = '''def compute_triage_priority(segments, vectors, events):
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

    return sorted(segments, key=lambda s: scores[s])'''

    new_triage = '''def compute_triage_priority(segments, vectors, events):
    """Determine triage priority order for incident response dispatch.

    Orders segments by total accumulated threat (vector sum). Segments with
    higher total threat are prioritized last (highest priority for response).
    """
    return sorted(segments, key=lambda s: sum(vectors[s]))'''

    content = content.replace(old_triage, new_triage)
    with open(path, "w") as f:
        f.write(content)


def regenerate_outputs():
    """Re-run the correlation with fixed code."""
    state_path = "/app/runtime/segment_state.jsonl"
    report_path = "/app/runtime/threat_assessment.jsonl"
    for p in [state_path, report_path]:
        if os.path.exists(p):
            os.remove(p)

    sys.path.insert(0, "/app/runtime")
    for mod_name in list(sys.modules.keys()):
        if mod_name in ("threat_accumulator", "correlation_analyzer", "threat_report",
                        "run_correlation", "intel_parser"):
            del sys.modules[mod_name]

    from run_correlation import run_correlation
    run_correlation()


if __name__ == "__main__":
    print("Applying fixes to threat correlation pipeline...")
    fix_threat_accumulator()
    print("  [1/3] Fixed threat_accumulator.py: moved self-increment after merge")
    fix_correlation_analyzer()
    print("  [2/3] Fixed correlation_analyzer.py: classification labels + triage metric")
    regenerate_outputs()
    print("  [3/3] Regenerated correlation outputs")
    print("Repair complete.")
