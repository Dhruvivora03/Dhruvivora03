"""
Repair script for threat intelligence correlation pipeline.

Fixes:
1. threat_accumulator.py: Add self-increment after CORRELATE merge
2. correlation_analyzer.py: Fix isolation predicate (incomparability, not equality)
3. correlation_analyzer.py: Fix triage ordering (by vector sum, not recency)
"""

import os
import sys


def fix_threat_accumulator():
    path = "/app/runtime/threat_accumulator.py"
    with open(path, "r") as f:
        content = f.read()

    old = '''    def apply_correlate(self, neighbor_intel):
        """Process CORRELATE — absorb neighbor's threat landscape.

        Performs component-wise maximum merge with the reported intel state.
        This is a purely passive operation — the segment gains awareness
        without experiencing any new adversarial activity. The merge is
        idempotent: correlating with the same intel multiple times produces
        the same result as correlating once.

        No self-increment is applied because the CORRELATE event is
        observational, not adversarial. The segment's true exposure is
        determined solely by PROBE and BREACH events targeting it directly.
        Adding a self-increment here would violate the separation between
        observation (learning about threats) and experience (being targeted
        by threats), corrupting the threat attribution model.
        """
        for segment in self.all_segments:
            if segment in neighbor_intel:
                incoming = int(neighbor_intel[segment])
                self._threat[segment] = max(self._threat[segment], incoming)'''

    new = '''    def apply_correlate(self, neighbor_intel):
        """Process CORRELATE — absorb neighbor's threat landscape and record event.

        Performs component-wise maximum merge, then increments the segment's
        own component to record the correlation as an observable event.
        """
        for segment in self.all_segments:
            if segment in neighbor_intel:
                incoming = int(neighbor_intel[segment])
                self._threat[segment] = max(self._threat[segment], incoming)
        self._threat[self.segment_id] += 1'''

    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)


def fix_correlation_analyzer():
    path = "/app/runtime/correlation_analyzer.py"
    with open(path, "r") as f:
        content = f.read()

    # Fix isolation predicate
    old_iso = '''def segments_are_isolated(vec_a, vec_b):
    """Determine if two segments have isolated threat profiles.

    Isolation requires symmetric boundedness: A <= B AND B <= A.

    When both directions hold, neither segment has observed threats
    exceeding the other's knowledge — their threat awareness has reached
    a fixed point of mutual consistency. This guarantees that separate
    IR teams handling each segment will have equivalent situational
    awareness, making independent handling safe.

    If either direction fails, one segment knows about threats the other
    doesn't, requiring joint handling to prevent blind spots.
    """
    return _vector_bounded_by(vec_a, vec_b) and _vector_bounded_by(vec_b, vec_a)'''

    new_iso = '''def _vector_dominates(vec_a, vec_b):
    """True if a >= b component-wise with at least one strict inequality."""
    return all(a >= b for a, b in zip(vec_a, vec_b)) and any(a > b for a, b in zip(vec_a, vec_b))


def segments_are_isolated(vec_a, vec_b):
    """Determine if two segments have isolated threat profiles.

    Isolation means neither vector dominates the other (incomparable).
    """
    return not _vector_dominates(vec_a, vec_b) and not _vector_dominates(vec_b, vec_a)'''

    content = content.replace(old_iso, new_iso)

    # Fix triage ordering
    old_triage = '''def compute_triage_priority(segments, vectors, events):
    """Compute triage ordering by temporal threat recency.

    Segments with more recent adversarial activity are prioritized higher
    in the triage queue, as ongoing operations require immediate containment
    while historical activity can be investigated post-incident.

    The recency score is the sequence number of the segment's most recent
    event. Higher recency = more urgent = later in the output ordering.
    """
    last_event_seq = {}
    for event in events:
        last_event_seq[event["segment_id"]] = event["seq"]
    return sorted(segments, key=lambda s: last_event_seq.get(s, 0))'''

    new_triage = '''def compute_triage_priority(segments, vectors, events):
    """Compute triage ordering by total threat severity (vector sum)."""
    return sorted(segments, key=lambda s: sum(vectors[s]))'''

    content = content.replace(old_triage, new_triage)
    with open(path, "w") as f:
        f.write(content)


def regenerate():
    state_path = "/app/runtime/segment_state.jsonl"
    report_path = "/app/runtime/threat_assessment.jsonl"
    for p in [state_path, report_path]:
        if os.path.exists(p):
            os.remove(p)
    sys.path.insert(0, "/app/runtime")
    for mod in list(sys.modules.keys()):
        if mod in ("threat_accumulator", "correlation_analyzer", "threat_report",
                   "run_correlation", "intel_parser"):
            del sys.modules[mod]
    from run_correlation import run_correlation
    run_correlation()


if __name__ == "__main__":
    fix_threat_accumulator()
    fix_correlation_analyzer()
    regenerate()
    print("Repair complete.")
