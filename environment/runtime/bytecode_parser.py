"""
Bytecode Parser Module
======================
Parses a simple register-based bytecode program from a text file.
Each instruction has the format:
    LABEL: OPCODE DEST, SRC1, SRC2
Registers are named r0-r9, with r0 being the zero register.
Memory operands are in the format mem[N].
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple


@dataclass
class Instruction:
    """Represents a single bytecode instruction."""
    label: str
    opcode: str
    dest: Optional[str]
    sources: List[str]
    raw_line: str
    block: str
    index: int

    def get_def(self) -> Set[str]:
        """Return the set of registers defined by this instruction."""
        if self.dest and self.dest.startswith('r') and self.dest != 'r0':
            return {self.dest}
        return set()

    def get_use(self) -> Set[str]:
        """Return the set of registers used by this instruction."""
        uses = set()
        for src in self.sources:
            if src.startswith('r') and src != 'r0':
                uses.add(src)
        return uses


def parse_instruction(line: str) -> Optional[Instruction]:
    """Parse a single instruction line into an Instruction object."""
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    # Match the label: opcode operands pattern
    match = re.match(r'(\w+):\s+(\w+)\s*(.*)', line)
    if not match:
        return None

    label = match.group(1)
    opcode = match.group(2)
    operands_str = match.group(3).strip()

    # Extract the basic block name
    block_match = re.match(r'(BB\d+)_(\d+)', label)
    if not block_match:
        return None
    block = block_match.group(1)
    index = int(block_match.group(2))

    # Parse operands based on opcode
    dest = None
    sources = []

    if opcode in ('LOAD',):
        # LOAD rX, mem[N]
        parts = [p.strip() for p in operands_str.split(',')]
        if len(parts) >= 1:
            dest = parts[0]
        if len(parts) >= 2:
            # mem[N] is not a register source
            mem_match = re.match(r'mem\[\d+\]', parts[1])
            if not mem_match and parts[1].startswith('r'):
                sources.append(parts[1])

    elif opcode in ('STORE',):
        # STORE mem[N], rX
        parts = [p.strip() for p in operands_str.split(',')]
        if len(parts) >= 2:
            sources.append(parts[1])

    elif opcode in ('ADD', 'SUB', 'MUL', 'DIV', 'AND', 'OR', 'XOR'):
        # OP rDest, rSrc1, rSrc2
        parts = [p.strip() for p in operands_str.split(',')]
        if len(parts) >= 1:
            dest = parts[0]
        for p in parts[1:]:
            if p.startswith('r'):
                sources.append(p)

    elif opcode == 'CMP':
        # CMP rA, rB (no dest, both are uses)
        parts = [p.strip() for p in operands_str.split(',')]
        for p in parts:
            if p.startswith('r'):
                sources.append(p)

    elif opcode == 'BRZ':
        # BRZ target_label (no register operands, branch uses condition flags)
        pass

    elif opcode == 'JMP':
        # JMP target_label
        pass

    elif opcode == 'PHI':
        # PHI rDest, rSrc1, rSrc2
        parts = [p.strip() for p in operands_str.split(',')]
        if len(parts) >= 1:
            dest = parts[0]
        for p in parts[1:]:
            if p.startswith('r'):
                sources.append(p)

    elif opcode == 'RET':
        # RET (no operands)
        pass

    return Instruction(
        label=label,
        opcode=opcode,
        dest=dest,
        sources=sources,
        raw_line=line,
        block=block,
        index=index
    )


def parse_program(filepath: str) -> List[Instruction]:
    """Parse a complete bytecode program from a file."""
    instructions = []
    with open(filepath, 'r') as f:
        for line in f:
            instr = parse_instruction(line)
            if instr is not None:
                instructions.append(instr)
    return instructions


def get_basic_blocks(instructions: List[Instruction]) -> dict:
    """Group instructions into basic blocks."""
    blocks = {}
    for instr in instructions:
        if instr.block not in blocks:
            blocks[instr.block] = []
        blocks[instr.block].append(instr)
    return blocks


def get_cfg_edges(instructions: List[Instruction]) -> List[Tuple[str, str]]:
    """
    Compute control flow graph edges between basic blocks.
    Returns list of (source_block, target_block) tuples.
    """
    blocks = get_basic_blocks(instructions)
    edges = []
    block_names = sorted(blocks.keys())

    for block_name in block_names:
        block_instrs = blocks[block_name]
        last_instr = block_instrs[-1]

        if last_instr.opcode == 'BRZ':
            # Conditional branch: target and fall-through
            target_match = re.match(r'(\w+)', last_instr.raw_line.split()[-1])
            if target_match:
                target_label = target_match.group(1)
                target_block = re.match(r'(BB\d+)', target_label)
                if target_block:
                    edges.append((block_name, target_block.group(1)))
            # Fall-through to next block
            idx = block_names.index(block_name)
            if idx + 1 < len(block_names):
                edges.append((block_name, block_names[idx + 1]))

        elif last_instr.opcode == 'JMP':
            # Unconditional jump
            target_match = re.match(r'(\w+)', last_instr.raw_line.split()[-1])
            if target_match:
                target_label = target_match.group(1)
                target_block = re.match(r'(BB\d+)', target_label)
                if target_block:
                    edges.append((block_name, target_block.group(1)))

        elif last_instr.opcode == 'RET':
            # No successors
            pass

        else:
            # Fall-through to next block
            idx = block_names.index(block_name)
            if idx + 1 < len(block_names):
                edges.append((block_name, block_names[idx + 1]))

    return edges
