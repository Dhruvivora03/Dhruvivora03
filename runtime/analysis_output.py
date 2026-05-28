"""
Analysis Output Module
======================
Produces the final analysis output files:
- liveness_results.jsonl: Per-instruction live-in and live-out sets
- analysis_summary.json: Interference graph, allocation priority, and fingerprint

This module aggregates results from the liveness engine, interference builder,
and allocation scorer to produce the complete analysis report.
"""

import json
import hashlib
from typing import Dict, List, Set

from bytecode_parser import Instruction
from liveness_engine import compute_liveness
from interference_builder import build_interference_graph, get_interference_count
from allocation_scorer import compute_allocation_priority


def generate_fingerprint(live_in: Dict[str, Set[str]], 
                         live_out: Dict[str, Set[str]],
                         interference: Dict[str, Set[str]],
                         priority: List) -> str:
    """
    Generate a deterministic fingerprint of the analysis results.
    This serves as a digest for validating correctness.
    """
    # Build a canonical string representation
    parts = []

    # Add live-in data
    for label in sorted(live_in.keys()):
        regs = ','.join(sorted(live_in[label]))
        parts.append(f"LI:{label}:{regs}")

    # Add live-out data
    for label in sorted(live_out.keys()):
        regs = ','.join(sorted(live_out[label]))
        parts.append(f"LO:{label}:{regs}")

    # Add interference data
    for reg in sorted(interference.keys()):
        neighbors = ','.join(sorted(interference[reg]))
        parts.append(f"IG:{reg}:{neighbors}")

    # Add priority data
    for reg, score in priority:
        parts.append(f"PR:{reg}:{score}")

    canonical = '|'.join(parts)
    return hashlib.sha256(canonical.encode()).hexdigest()[:32]


def produce_liveness_jsonl(instructions: List[Instruction], output_path: str):
    """Write per-instruction liveness results to a JSONL file."""
    live_in, live_out = compute_liveness(instructions)

    with open(output_path, 'w') as f:
        for instr in instructions:
            record = {
                "label": instr.label,
                "opcode": instr.opcode,
                "live_in": sorted(list(live_in[instr.label])),
                "live_out": sorted(list(live_out[instr.label]))
            }
            f.write(json.dumps(record) + '\n')


def produce_analysis_summary(instructions: List[Instruction], output_path: str):
    """Write the complete analysis summary to a JSON file."""
    live_in, live_out = compute_liveness(instructions)
    interference = build_interference_graph(instructions)
    priority = compute_allocation_priority(instructions)
    interference_count = get_interference_count(instructions)

    # Serialize interference graph
    interference_serial = {}
    for reg in sorted(interference.keys()):
        interference_serial[reg] = sorted(list(interference[reg]))

    # Generate fingerprint for validation
    fingerprint = generate_fingerprint(live_in, live_out, interference, priority)

    summary = {
        "program_stats": {
            "num_instructions": len(instructions),
            "num_registers_used": len(interference),
            "num_interference_edges": interference_count
        },
        "interference_graph": interference_serial,
        "allocation_priority": [{"register": reg, "score": score} for reg, score in priority],
        "allocation_order": [reg for reg, _ in priority],
        "fingerprint": fingerprint
    }

    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)


def run_full_analysis(instructions: List[Instruction], output_dir: str = "."):
    """Run the complete analysis pipeline and write output files."""
    import os
    liveness_path = os.path.join(output_dir, "liveness_results.jsonl")
    summary_path = os.path.join(output_dir, "analysis_summary.json")

    produce_liveness_jsonl(instructions, liveness_path)
    produce_analysis_summary(instructions, summary_path)

    return liveness_path, summary_path
