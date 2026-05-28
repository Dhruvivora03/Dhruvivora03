"""
Lattice thermal diffusion simulation orchestrator.
Coordinates parsing, engine processing, analysis, and report generation.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from log_parser import parse_thermal_log, get_all_nodes
from diffusion_engine import ThermalNode
from lattice_analyzer import analyze_lattice
from thermal_report import write_state_file, write_summary_report


def run():
    """Execute the full simulation pipeline."""
    # Step 1: Parse the thermal trace log
    events = parse_thermal_log()
    all_nodes = get_all_nodes(events)

    # Step 2: Initialize thermal nodes
    node_engines = {}
    for node_id in all_nodes:
        node_engines[node_id] = ThermalNode(node_id, all_nodes)

    # Step 3: Process events through the diffusion engine
    for event in events:
        node_id = event["node_id"]
        engine = node_engines[node_id]

        if event["event_type"] == "DIFFUSE":
            engine.apply_diffuse()
        elif event["event_type"] == "CONVECT":
            engine.apply_convect()
        elif event["event_type"] == "EQUILIBRATE":
            engine.apply_equilibrate(event["detail"])

    # Step 4: Collect final vectors
    vectors_dict = {}
    for node_id in all_nodes:
        vectors_dict[node_id] = node_engines[node_id].get_vector()

    # Step 5: Run lattice analysis
    analysis = analyze_lattice(all_nodes, vectors_dict, events)

    # Step 6: Write output files
    records = write_state_file(all_nodes, vectors_dict, events, analysis)
    summary = write_summary_report(records, analysis)

    print(f"Simulation complete. Digest: {summary['digest']}")
    print(f"Nodes: {summary['total_nodes']}, Independent pairs: {summary['independent_pair_count']}")
    print(f"Priority order: {summary['priority_order']}")

    return summary


if __name__ == "__main__":
    run()
