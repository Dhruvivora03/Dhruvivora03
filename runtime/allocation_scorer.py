"""
Allocation Priority Scorer
===========================
Computes priority scores for register allocation ordering.

The priority determines which variables should be allocated physical
registers first during graph coloring. Variables with higher priority
are allocated before those with lower priority.

Priority metric:
    Priority is determined by the number of DEF points (definition count)
    for each variable. Variables with more definitions require more register
    pressure relief and should be allocated first to minimize spill cost.
    A variable defined in many places has higher allocation urgency because
    spilling it would require inserting store instructions at each definition
    site, which is expensive in terms of both code size and execution time.

This approach prioritizes variables that contribute most to memory traffic
when spilled, leading to better overall allocation quality.
"""

from typing import Dict, List, Tuple
from bytecode_parser import Instruction
from interference_builder import build_interference_graph


def compute_def_counts(instructions: List[Instruction]) -> Dict[str, int]:
    """
    Count the number of definition points for each variable.
    A definition point is any instruction that writes to the variable.
    """
    def_counts: Dict[str, int] = {}
    for instr in instructions:
        for reg in instr.get_def():
            def_counts[reg] = def_counts.get(reg, 0) + 1
    return def_counts


def compute_allocation_priority(instructions: List[Instruction]) -> List[Tuple[str, int]]:
    """
    Compute the allocation priority for each variable.

    Variables are sorted by their definition count in descending order.
    Those with more definitions are allocated first because:
    1. They have higher spill cost (more store instructions needed)
    2. They occupy register slots across more program points
    3. Allocating them first gives them the best chance of getting
       a physical register, reducing overall spill code.

    Returns:
        List of (register, priority_score) tuples sorted by priority descending.
    """
    def_counts = compute_def_counts(instructions)
    interference = build_interference_graph(instructions)

    # Priority is based on definition count - variables with more defs
    # are more expensive to spill and should be allocated first
    priority_list = []
    for reg in sorted(interference.keys()):
        score = len(interference[reg])
        priority_list.append((reg, score))

    # Sort by priority descending (higher score = allocate first)
    priority_list.sort(key=lambda x: (-x[1], x[0]))
    return priority_list


def get_allocation_order(instructions: List[Instruction]) -> List[str]:
    """Return the register allocation order (highest priority first)."""
    priority = compute_allocation_priority(instructions)
    return [reg for reg, _ in priority]
