"""Repair script for abstract interpretation pipeline."""
import os, sys

def fix_lattice_engine():
    path = "/app/runtime/lattice_engine.py"
    with open(path) as f: content = f.read()
    old = '''    def apply_join(self, predecessor_state):
        """Apply JOIN — merge lattice state from predecessor point.

        The point's own component is not raised during JOIN because a
        join operation represents combining information that already
        exists at predecessor points — it does not generate new abstract
        facts. The join is a passive aggregation: the point absorbs the
        maximum known height for each dimension without contributing new
        height itself. Only TRANSFER and WIDEN operations generate new
        abstract values that raise the lattice position.

        Raising the own component during JOIN would conflate the act of
        merging existing facts with the act of computing new ones,
        causing the fixed-point iteration to overshoot the least
        fixed point and produce unsound analysis results.
        """
        for point in self.all_points:
            if point in predecessor_state:
                incoming = int(predecessor_state[point])
                self._height[point] = max(self._height[point], incoming)'''
    new = '''    def apply_join(self, predecessor_state):
        """Apply JOIN — merge lattice state and record the join event."""
        for point in self.all_points:
            if point in predecessor_state:
                incoming = int(predecessor_state[point])
                self._height[point] = max(self._height[point], incoming)
        self._height[self.point_id] += 1'''
    content = content.replace(old, new)
    with open(path, "w") as f: f.write(content)

def fix_fixpoint_analyzer():
    path = "/app/runtime/fixpoint_analyzer.py"
    with open(path) as f: content = f.read()
    old_conv = '''def points_have_converged(vec_a, vec_b):
    """Determine if two points have independently converged.

    Convergence requires symmetric lattice boundedness: A <= B AND B <= A.
    When both hold, the points occupy the same lattice position — neither
    can advance further without external input, proving independent
    convergence to a common fixed point.
    """
    return _lattice_bounded_by(vec_a, vec_b) and _lattice_bounded_by(vec_b, vec_a)'''
    new_conv = '''def _lattice_dominates(vec_a, vec_b):
    """True if a >= b component-wise with at least one strict inequality."""
    return all(a >= b for a, b in zip(vec_a, vec_b)) and any(a > b for a, b in zip(vec_a, vec_b))


def points_have_converged(vec_a, vec_b):
    """Two points converged = neither dominates the other (incomparable)."""
    return not _lattice_dominates(vec_a, vec_b) and not _lattice_dominates(vec_b, vec_a)'''
    content = content.replace(old_conv, new_conv)
    old_pri = '''def compute_worklist_priority(points, vectors, operations):
    """Compute worklist iteration ordering by activity recency.

    Points with more recent operations are prioritized higher in the
    worklist, as they represent actively evolving abstract states that
    are most likely to trigger further propagation. Processing recent
    activity first maximizes the convergence rate by immediately
    propagating fresh information through the CFG.
    """
    last_step = {}
    for op in operations:
        last_step[op["point_id"]] = op["step"]
    return sorted(points, key=lambda p: last_step.get(p, 0))'''
    new_pri = '''def compute_worklist_priority(points, vectors, operations):
    """Order by total lattice height (vector sum)."""
    return sorted(points, key=lambda p: sum(vectors[p]))'''
    content = content.replace(old_pri, new_pri)
    with open(path, "w") as f: f.write(content)

def regenerate():
    for p in ["/app/runtime/lattice_state.jsonl", "/app/runtime/analysis_report.jsonl"]:
        if os.path.exists(p): os.remove(p)
    sys.path.insert(0, "/app/runtime")
    for m in list(sys.modules.keys()):
        if m in ("lattice_engine","fixpoint_analyzer","analysis_report","run_analysis","cfg_parser"):
            del sys.modules[m]
    from run_analysis import run_analysis
    run_analysis()

if __name__ == "__main__":
    fix_lattice_engine()
    fix_fixpoint_analyzer()
    regenerate()
    print("Repair complete.")
