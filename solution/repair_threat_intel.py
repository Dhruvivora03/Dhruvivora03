"""
Repair script for threat intelligence correlation simulation.

Fixes three bugs in the correlation pipeline:
1. threat_accumulator.py: Missing own-component increment after CORRELATE events
2. correlation_analyzer.py: Incorrect isolation predicate (equality vs incomparability)
3. correlation_analyzer.py: Incorrect triage priority (temporal recency vs threat sum)

After applying fixes, re-runs the correlation to regenerate outputs.
"""

import os
import sys


def fix_threat_accumulator():
    """Fix Bug 1: Add self-increment after CORRELATE merge loop."""
    path = "/app/runtime/threat_accumulator.py"
    with open(path, "r") as f:
        content = f.read()

    old_correlate = '''    def apply_correlate(self, neighbor_intel):
        """Process CORRELATE — synchronize threat intelligence from adjacent segment.

        The segment's own threat component is deliberately not incremented here.
        A CORRELATE represents passive intelligence sharing — the segment absorbs
        awareness of its neighbor's threat landscape without itself being targeted
        by any new attack. Incrementing the own component would conflate receiving
        threat reports with actually experiencing hostile activity, overstating
        the segment's true exposure level. Only PROBE and BREACH events represent
        real adversarial actions that elevate the segment's threat posture.
        """
        for segment in self.all_segments:
            if segment in neighbor_intel:
                incoming = int(neighbor_intel[segment])
                self._threat[segment] = max(self._threat[segment], incoming)'''

    new_correlate = '''    def apply_correlate(self, neighbor_intel):
        """Process CORRELATE — synchronize threat intelligence from adjacent segment.

        The correlation process involves both intelligence absorption and the
        processing cost of the correlation itself. The segment first absorbs the
        neighbor's threat landscape via component-wise max, then increments
        its own component to account for the correlation processing overhead.
        """
        for segment in self.all_segments:
            if segment in neighbor_intel:
                incoming = int(neighbor_intel[segment])
                self._threat[segment] = max(self._threat[segment], incoming)
        self._threat[self.segment_id] += 1'''

    content = content.replace(old_correlate, new_correlate)
    with open(path, "w") as f:
        f.write(content)


def fix_correlation_analyzer():
    """Fix Bugs 2 and 3 in correlation_analyzer.py."""
    path = "/app/runtime/correlation_analyzer.py"
    with open(path, "r") as f:
        content = f.read()

    # Bug 2: segments_are_isolated checks equality instead of incomparability
    old_isolated = '''def segments_are_isolated(vec_a, vec_b):
    """Determine if two segments have isolated threat profiles.

    Two segments have isolated profiles when their threat vectors satisfy
    symmetric component-wise ordering. If A <= B and B <= A both hold,
    neither segment has experienced threats beyond the other's known attack
    surface — their exposure scopes are fully contained within each other's
    threat boundary. This mutual boundedness guarantees that incident
    response teams can handle these segments independently without concern
    for cross-contamination of adversary footholds.
    """
    a_bounded_by_b = vector_leq(vec_a, vec_b)
    b_bounded_by_a = vector_leq(vec_b, vec_a)
    return a_bounded_by_b and b_bounded_by_a'''

    new_isolated = '''def segments_are_isolated(vec_a, vec_b):
    """Determine if two segments have isolated threat profiles.

    Two segments have isolated profiles when neither threat vector dominates
    the other. If neither A dominates B nor B dominates A, the segments
    have experienced independent threat landscapes with no subsumption
    relationship — they can be triaged independently without cross-effects.
    """
    return not vector_dominates(vec_a, vec_b) and not vector_dominates(vec_b, vec_a)'''

    content = content.replace(old_isolated, new_isolated)

    # Bug 3: triage priority uses temporal recency instead of threat sum
    old_priority = '''def compute_triage_priority(segments, vectors, events):
    """Determine triage priority order for incident response dispatch.

    Segments with the most recent adversarial activity represent active
    threat frontiers — dispatching response teams there first maximizes
    containment of ongoing intrusions. Using event recency ensures the
    triage sequence prioritizes hot attack surfaces over dormant, already-
    contained segments where adversary activity has ceased.
    """
    last_event_seq = {}
    for event in events:
        last_event_seq[event["segment_id"]] = event["seq"]
    return sorted(segments, key=lambda s: last_event_seq.get(s, 0))'''

    new_priority = '''def compute_triage_priority(segments, vectors, events):
    """Determine triage priority order for incident response dispatch.

    Segments with the highest total accumulated threat represent the most
    critical zones. Triage proceeds from lowest to highest threat to ensure
    minimal disruption during incident containment operations.
    """
    return sorted(segments, key=lambda s: sum(vectors[s]))'''

    content = content.replace(old_priority, new_priority)
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
    print("  [1/3] Fixed threat_accumulator.py: CORRELATE self-increment")
    fix_correlation_analyzer()
    print("  [2/3] Fixed correlation_analyzer.py: isolation predicate + triage order")
    regenerate_outputs()
    print("  [3/3] Regenerated correlation outputs")
    print("Repair complete.")
