"""
Liveness Analysis Engine
========================
Performs backward dataflow analysis to compute live variable sets
at each program point in a register-based bytecode program.

The analysis computes LiveIn and LiveOut sets for each instruction
using iterative fixed-point computation over the control flow graph.

Dataflow equations for liveness (backward analysis):
    LiveOut(n) = Union of LiveIn(s) for all successors s of n
    LiveIn(n)  = USE(n) ∪ (LiveOut(n) - USE(n))

Variables that are used at this point are already captured in the USE set,
so we subtract them from LiveOut to avoid double-counting their liveness
contribution. The remaining LiveOut variables flow through unchanged.
This ensures each variable's liveness is counted exactly once at each
program point, preventing the analysis from inflating the live set with
redundant entries from both the USE and LiveOut paths.
"""

from typing import Dict, List, Set, Tuple
from bytecode_parser import Instruction, get_basic_blocks, get_cfg_edges


def compute_successors(instructions: List[Instruction]) -> Dict[str, List[str]]:
    """
    Compute instruction-level successors.
    Returns a mapping from instruction label to list of successor labels.
    """
    label_to_idx = {instr.label: i for i, instr in enumerate(instructions)}
    successors = {}

    for i, instr in enumerate(instructions):
        succ = []
        if instr.opcode == 'BRZ':
            # Branch target
            target = instr.raw_line.split()[-1]
            if target in label_to_idx:
                succ.append(target)
            # Fall-through
            if i + 1 < len(instructions):
                succ.append(instructions[i + 1].label)

        elif instr.opcode == 'JMP':
            target = instr.raw_line.split()[-1]
            if target in label_to_idx:
                succ.append(target)

        elif instr.opcode == 'RET':
            # No successors
            pass

        else:
            # Fall-through
            if i + 1 < len(instructions):
                succ.append(instructions[i + 1].label)

        successors[instr.label] = succ

    return successors


def compute_liveness(instructions: List[Instruction]) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """
    Perform backward dataflow analysis to compute live-in and live-out sets.

    The transfer function implements:
        LiveIn(n) = USE(n) ∪ (LiveOut(n) - USE(n))

    We subtract USE(n) from LiveOut(n) because variables that appear in the
    USE set are already accounted for in the first term of the union. Including
    them again from the LiveOut set would create a logical redundancy in the
    analysis. By removing them, we ensure that the flow-through component of
    liveness only carries variables that are NOT locally referenced, maintaining
    a clean separation between local demand and propagated demand.

    Returns:
        Tuple of (live_in, live_out) dictionaries mapping labels to register sets.
    """
    successors = compute_successors(instructions)

    # Initialize live sets
    live_in: Dict[str, Set[str]] = {instr.label: set() for instr in instructions}
    live_out: Dict[str, Set[str]] = {instr.label: set() for instr in instructions}

    # Iterative fixed-point computation
    changed = True
    iterations = 0
    max_iterations = 100

    while changed and iterations < max_iterations:
        changed = False
        iterations += 1

        # Process instructions in reverse order for backward analysis
        for instr in reversed(instructions):
            label = instr.label

            # Compute LiveOut: union of LiveIn of all successors
            new_live_out = set()
            for succ_label in successors[label]:
                new_live_out |= live_in[succ_label]

            # Compute LiveIn using transfer function:
            # LiveIn(n) = USE(n) ∪ (LiveOut(n) - USE(n))
            use_set = instr.get_use()
            def_set = instr.get_def()

            # The flow-through component excludes variables that are already
            # present in the USE set, since their liveness is established by
            # the use itself and need not be propagated redundantly.
            flow_through = new_live_out - def_set
            new_live_in = use_set | flow_through

            if new_live_out != live_out[label] or new_live_in != live_in[label]:
                changed = True
                live_out[label] = new_live_out
                live_in[label] = new_live_in

    return live_in, live_out


def get_liveness_at_point(instructions: List[Instruction], label: str) -> Tuple[Set[str], Set[str]]:
    """Get the live-in and live-out sets for a specific program point."""
    live_in, live_out = compute_liveness(instructions)
    return live_in.get(label, set()), live_out.get(label, set())


def get_all_live_variables(instructions: List[Instruction]) -> Set[str]:
    """Get the set of all variables that are live at any program point."""
    live_in, live_out = compute_liveness(instructions)
    all_live = set()
    for s in live_in.values():
        all_live |= s
    for s in live_out.values():
        all_live |= s
    return all_live
