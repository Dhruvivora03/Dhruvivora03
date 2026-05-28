"""
Analysis Orchestrator
=====================
Main entry point for running the complete dataflow liveness analysis
on a bytecode program. Coordinates parsing, analysis, and output generation.
"""

import sys
import os

# Add the runtime directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bytecode_parser import parse_program
from analysis_output import run_full_analysis


def main():
    """Run the complete analysis pipeline."""
    # Determine input and output paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    input_file = os.path.join(data_dir, "bytecode_program.txt")

    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    # Parse the program
    print(f"Parsing bytecode program: {input_file}")
    instructions = parse_program(input_file)
    print(f"  Found {len(instructions)} instructions")

    # Determine output directory
    output_dir = os.environ.get("OUTPUT_DIR", script_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Run the analysis
    print(f"Running liveness analysis...")
    liveness_path, summary_path = run_full_analysis(instructions, output_dir)

    print(f"Analysis complete!")
    print(f"  Liveness results: {liveness_path}")
    print(f"  Analysis summary: {summary_path}")


if __name__ == "__main__":
    main()
