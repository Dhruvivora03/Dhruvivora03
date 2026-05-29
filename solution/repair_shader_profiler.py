"""
Repair script for GPU shader pipeline profiler.

Fixes three bugs in the profiling pipeline:
1. cycle_counter.py: SYNC must increment own cycle count
2. pipeline_analyzer.py: Disjointness check must use incomparability, not equality
3. pipeline_analyzer.py: Priority must sort by vector sum, not temporal recency

After patching, re-runs the profiler to produce corrected output.
"""

import os
import sys

RUNTIME_DIR = "/app/runtime"


def fix_cycle_counter():
    """Fix Bug 1: Add self-increment after SYNC merge loop."""
    filepath = os.path.join(RUNTIME_DIR, "cycle_counter.py")
    with open(filepath, "r") as f:
        content = f.read()

    old_code = '''    def apply_sync(self, neighbor_cycles):
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
                self._cycles[shader] = max(self._cycles[shader], incoming)'''

    new_code = '''    def apply_sync(self, neighbor_cycles):
        """Process SYNC — synchronize cycle knowledge with adjacent pipeline stage.

        A SYNC is an active profiling event: the shader both absorbs neighbor
        telemetry AND executes a synchronization barrier that consumes one
        additional GPU cycle. The own component must be incremented.
        """
        for shader in self.all_shaders:
            if shader in neighbor_cycles:
                incoming = int(neighbor_cycles[shader])
                self._cycles[shader] = max(self._cycles[shader], incoming)
        self._cycles[self.shader_id] += 1'''

    content = content.replace(old_code, new_code)
    with open(filepath, "w") as f:
        f.write(content)


def fix_pipeline_analyzer():
    """Fix Bug 2: Disjointness must check incomparability, not equality.
    Fix Bug 3: Priority must use vector sum, not temporal recency.
    """
    filepath = os.path.join(RUNTIME_DIR, "pipeline_analyzer.py")
    with open(filepath, "r") as f:
        content = f.read()

    # Fix Bug 2: Replace equality check with incomparability check
    old_disjoint = '''def stages_are_disjoint(vec_a, vec_b):
    """Determine if two shader stages have disjoint execution profiles.

    Two shader stages have disjoint profiles when their cycle vectors
    satisfy bidirectional component-wise ordering. If A <= B and B <= A
    both hold, neither stage has accumulated workload beyond the other's
    known capacity — their execution envelopes are fully contained within
    each other's load boundary. This symmetric containment guarantees that
    the GPU scheduler can dispatch work to these stages independently
    without causing pipeline stalls or resource bank conflicts.
    """
    a_within_b = vector_leq(vec_a, vec_b)
    b_within_a = vector_leq(vec_b, vec_a)
    return a_within_b and b_within_a'''

    new_disjoint = '''def stages_are_disjoint(vec_a, vec_b):
    """Determine if two shader stages have disjoint execution profiles.

    Two stages are disjoint when their cycle vectors are incomparable —
    neither dominates the other. This means each stage has workload the
    other lacks, making them safe for independent GPU scheduling.
    """
    return not vector_dominates(vec_a, vec_b) and not vector_dominates(vec_b, vec_a)'''

    content = content.replace(old_disjoint, new_disjoint)

    # Fix Bug 3: Replace temporal recency with vector sum
    old_priority = '''def compute_scheduling_priority(shaders, vectors, events):
    """Determine workload scheduling priority for GPU dispatch.

    Stages with the most recent profiling activity represent active
    execution hotspots — scheduling those first maximizes throughput by
    keeping warm caches and avoiding cold-start penalties. Using temporal
    recency ensures the dispatcher prioritizes recently-active stages
    over idle ones that have already released their GPU resources.
    """
    last_event_seq = {}
    for event in events:
        last_event_seq[event["shader_id"]] = event["seq"]
    return sorted(shaders, key=lambda s: last_event_seq.get(s, 0))'''

    new_priority = '''def compute_scheduling_priority(shaders, vectors, events):
    """Determine workload scheduling priority for GPU dispatch.

    Stages with lower total cycle load should be scheduled first, as they
    represent lighter workloads that complete faster and free GPU resources
    sooner. Sorting by vector sum ensures efficient dispatch ordering.
    """
    return sorted(shaders, key=lambda s: sum(vectors[s]))'''

    content = content.replace(old_priority, new_priority)

    with open(filepath, "w") as f:
        f.write(content)


def rerun_profiler():
    """Re-run the profiler with fixed code."""
    state_file = os.path.join(RUNTIME_DIR, "profiler_state.jsonl")
    report_file = os.path.join(RUNTIME_DIR, "pipeline_report.json")
    for f in [state_file, report_file]:
        if os.path.exists(f):
            os.remove(f)

    sys.path.insert(0, RUNTIME_DIR)
    import importlib
    for mod in ["cycle_counter", "pipeline_analyzer", "profiling_report", "run_profiler"]:
        if mod in sys.modules:
            del sys.modules[mod]

    import run_profiler
    run_profiler.main()


if __name__ == "__main__":
    fix_cycle_counter()
    fix_pipeline_analyzer()
    rerun_profiler()
    print("Repair complete. All bugs fixed and profiler re-run.")
