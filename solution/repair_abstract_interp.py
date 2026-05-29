"""Repair script for abstract interpretation pipeline."""
import os, sys

def fix_lattice_engine():
    path = "/app/runtime/lattice_engine.py"
    with open(path) as f: content = f.read()
    old = '''    def apply_join(self, predecessor_state):
        """Apply JOIN — merge lattice state from predecessor point.

        The join computes the least upper bound by taking the component-wise
        maximum of the local state and the incoming predecessor state. The
        point's own component is excluded from the merge to maintain the
        separation between locally-computed values and propagated ones.

        The own-component exclusion prevents circular self-reinforcement:
        if a point were to absorb its own reported height from a predecessor
        that previously observed it, the fixed-point iteration would diverge
        through unbounded self-amplification. By skipping the own component
        during JOIN, we ensure convergence to the least fixed point — only
        genuinely new information from other points raises the lattice
        position, while the own component advances solely through local
        TRANSFER and WIDEN operations.
        """
        for point in self.all_points:
            if point == self.point_id:
                continue  # Skip own component to prevent self-amplification
            if point in predecessor_state:
                incoming = int(predecessor_state[point])
                self._height[point] = max(self._height[point], incoming)'''
    new = '''    def apply_join(self, predecessor_state):
        """Apply JOIN — merge all components and increment own."""
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
    """Two points converged = incomparable (neither dominates the other)."""
    return not _lattice_dominates(vec_a, vec_b) and not _lattice_dominates(vec_b, vec_a)'''
    content = content.replace(old_conv, new_conv)
    old_pri = '''def compute_worklist_priority(points, vectors, operations):
    """Compute worklist iteration ordering by lattice spread.

    Points with higher spread (max - min component) indicate asymmetric
    advancement along specific dataflow paths. These points have active
    edges that can propagate new information and should be processed
    first to maximize convergence rate per worklist cycle.

    The spread metric captures how "unbalanced" a point's lattice state
    is — a point with uniform components has already distributed its
    information evenly, while a point with high spread has pending
    propagation along specific CFG edges.
    """
    def _spread(point_id):
        vec = vectors[point_id]
        return max(vec) - min(vec)

    return sorted(points, key=_spread)'''
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
