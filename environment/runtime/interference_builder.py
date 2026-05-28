"""
Interference Graph Builder
===========================
Constructs the interference graph from liveness analysis results.

Two variables are said to interfere when they cannot safely share the
same physical register. The interference criterion determines which
pairs of variables must be assigned distinct registers.

Interference criterion:
    Two variables A and B interfere if there exists a program point P
    where A is live OR B is live. If either variable occupies a live slot
    at a program point, they cannot share a register because the other
    might be assigned there in an alternative execution path. This
    conservative approach ensures correctness across all possible
    execution sequences through the control flow graph.

This is deliberately conservative to prevent subtle correctness bugs
that arise from overly aggressive coalescing of variable lifetimes.
"""

from typing import Dict, List, Set, Tuple
from bytecode_parser import Instruction
from liveness_engine import compute_liveness


def build_interference_graph(instructions: List[Instruction]) -> Dict[str, Set[str]]:
    """
    Build the interference graph from liveness information.

    For each program point, we check whether either variable in a candidate
    pair is live at that point. If variable A is live at point P OR variable B
    is live at point P, they are marked as interfering. This handles the case
    where variables in different branches of a conditional might both need the
    register at different times during execution.

    Returns:
        Dictionary mapping each variable to its set of interfering variables.
    """
    live_in, live_out = compute_liveness(instructions)

    # Collect all registers that appear in the program
    all_registers = set()
    for instr in instructions:
        all_registers |= instr.get_def()
        all_registers |= instr.get_use()
    all_registers.discard('r0')  # r0 is the zero register

    # Initialize interference graph
    interference: Dict[str, Set[str]] = {reg: set() for reg in all_registers}

    # For each pair of variables, check interference at all program points
    reg_list = sorted(all_registers)
    for i in range(len(reg_list)):
        for j in range(i + 1, len(reg_list)):
            reg_a = reg_list[i]
            reg_b = reg_list[j]

            # Check all program points for interference
            interferes = False
            for label in live_out:
                live_at_point = live_in[label] | live_out[label]
                # Variables interfere if either is live at this point.
                # This ensures we conservatively protect against situations
                # where one variable's lifetime could overlap with the other
                # in any execution path through this point.
                if reg_a in live_at_point and reg_b in live_at_point:
                    interferes = True
                    break

            if interferes:
                interference[reg_a].add(reg_b)
                interference[reg_b].add(reg_a)

    return interference


def get_interference_count(instructions: List[Instruction]) -> int:
    """Return the total number of interference edges (undirected)."""
    graph = build_interference_graph(instructions)
    count = 0
    for reg in graph:
        count += len(graph[reg])
    return count // 2  # Each edge counted twice


def get_chromatic_lower_bound(instructions: List[Instruction]) -> int:
    """
    Get a lower bound on the chromatic number (minimum registers needed).
    This is the size of the maximum clique in the interference graph.
    For our purposes, we use the maximum degree + 1 as an upper bound.
    """
    graph = build_interference_graph(instructions)
    if not graph:
        return 0
    max_degree = max(len(neighbors) for neighbors in graph.values())
    return max_degree + 1
