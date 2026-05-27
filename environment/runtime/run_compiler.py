"""Entry point for the bytecode compiler.

Compiles all configured source files, optimizes the bytecode,
and writes output JSON files with compilation results and statistics.
"""

import json
import os

from runtime.compiler import BatchCompiler


def main():
    """Run the batch compiler and write output files."""
    config_path = os.path.join(os.path.dirname(__file__), "config.ini")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    compiler = BatchCompiler(config_path)
    units = compiler.compile_all()
    stats = compiler.aggregate_stats()

    # Write compilation results
    results = {
        "compilation_units": [],
    }
    for unit in units:
        results["compilation_units"].append({
            "filename": unit.filename,
            "raw_instructions": [i.to_dict() for i in unit.raw_bytecode],
            "optimized_instructions": [i.to_dict() for i in unit.optimized_bytecode],
            "symbol_table": unit.symbols,
            "raw_count": unit.raw_count,
            "optimized_count": unit.optimized_count,
        })

    with open(os.path.join(output_dir, "compilation_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    # Write statistics
    with open(os.path.join(output_dir, "compiler_stats.json"), "w") as f:
        json.dump(stats, f, indent=2)


if __name__ == "__main__":
    main()
