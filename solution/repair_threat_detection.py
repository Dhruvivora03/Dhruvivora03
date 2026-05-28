"""
Repair script for the network intrusion detection pipeline.
Fixes bugs in propagation_model.py and segment_classifier.py, then
re-runs the detection pipeline to produce correct output.
"""

import sys
import os
import re

sys.path.insert(0, "/app/runtime")

# ============================================================
# Fix Bug 1: propagation_model.py - conditional attribution only when
# adjacent reports higher. Should always attribute after lateral.
# ============================================================

model_path = "/app/runtime/propagation_model.py"
with open(model_path, "r") as fh:
    lines = fh.readlines()

fixed_lines = []
in_lateral = False
i = 0
while i < len(lines):
    line = lines[i]

    if 'def process_lateral(state, segment, adjacent_report):' in line:
        in_lateral = True
        fixed_lines.append(line)
        i += 1
        continue

    if in_lateral:
        if 'own_before = state[segment][segment]' in line:
            i += 1
            continue

        if '# Attribute only if genuine threat escalation was received' in line:
            i += 1
            while i < len(lines) and ('if state[segment][segment] > own_before' in lines[i]
                                       or 'state[segment][segment] += 1' in lines[i]
                                       or lines[i].strip() == ''):
                i += 1
            fixed_lines.append('    state[segment][segment] += 1\n')
            fixed_lines.append('\n')
            in_lateral = False
            continue

        if line.strip().startswith('def ') and 'process_lateral' not in line:
            in_lateral = False

    fixed_lines.append(line)
    i += 1

with open(model_path, "w") as fh:
    fh.writelines(fixed_lines)


# ============================================================
# Fix Bug 2: segment_classifier.py - isolation uses uniform polarity
# (checks dominance = comparable) instead of mixed polarity
# (checks incomparability = truly isolatable)
# ============================================================

classifier_path = "/app/runtime/segment_classifier.py"
with open(classifier_path, "r") as fh:
    code = fh.read()

old_isolation = re.compile(
    r'def can_isolate_segments\(threat_vec_a, threat_vec_b\):.*?'
    r'return has_uniform_polarity\(deltas\)',
    re.DOTALL
)

new_isolation = '''def can_isolate_segments(threat_vec_a, threat_vec_b):
    """Determine if two segments can be safely isolated.

    Segments are isolatable when their difference has mixed polarity
    (incomparable -- neither subsumes the other).
    """
    deltas = subtract_vectors(threat_vec_a, threat_vec_b)
    has_pos = any(d > 0 for d in deltas)
    has_neg = any(d < 0 for d in deltas)
    return has_pos and has_neg'''

code = old_isolation.sub(new_isolation, code)


# ============================================================
# Fix Bug 3: triage uses L2 norm instead of simple sum
# ============================================================

old_triage = re.compile(
    r'def compute_triage_priority\(segments, threat_vectors, events\):.*?'
    r'return sorted\(segments, key=geometric_magnitude\)',
    re.DOTALL
)

new_triage = '''def compute_triage_priority(segments, threat_vectors, events):
    """Compute triage order by total threat sum (ascending)."""
    return sorted(segments, key=lambda s: sum(threat_vectors[s]))'''

code = old_triage.sub(new_triage, code)

with open(classifier_path, "w") as fh:
    fh.write(code)


# ============================================================
# Re-run detection with fixed code
# ============================================================

for path in ["/app/runtime/detection_findings.jsonl", "/app/runtime/detection_summary.json"]:
    if os.path.exists(path):
        os.remove(path)

for mod in list(sys.modules.keys()):
    if mod in ("propagation_model", "segment_classifier", "detection_report",
               "run_detection", "event_parser"):
        del sys.modules[mod]

from run_detection import run
run()
