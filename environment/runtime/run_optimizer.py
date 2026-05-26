"""Main entry point for the IR optimization engine.

Orchestrates module loading, instruction ordering, optimization pass
execution, metrics computation, and report generation.
"""

import json
import os

from runtime.module_loader import ModuleLoader
from runtime.pass_engine import PassEngine
from runtime.report_builder import ReportBuilder


def main():
    """Run the IR optimization engine end-to-end."""
    config_path = os.path.join(os.path.dirname(__file__), "config.ini")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Stage 1: Load IR instruction modules
    loader = ModuleLoader(config_path)
    instructions = loader.load_all_instructions()

    # Stage 2: Order instructions for processing
    engine = PassEngine(config_path)
    ordered = engine.order_instructions(instructions)

    # Stage 3: Run optimization passes
    ctx = engine.run_passes(ordered)

    # Stage 4: Compute window metrics
    window_metrics = engine.compute_window_metrics(ordered, ctx)

    # Stage 5: Build and write outputs
    builder = ReportBuilder(ordered, ctx, window_metrics)

    opt_report = builder.build_optimization_report()
    opt_report["pass_depth"] = engine.pass_depth

    analysis_report = builder.build_analysis_report()

    with open(os.path.join(output_dir, "optimization_report.json"), "w") as f:
        json.dump(opt_report, f, indent=2)

    with open(os.path.join(output_dir, "analysis_metrics.json"), "w") as f:
        json.dump(analysis_report, f, indent=2)


if __name__ == "__main__":
    main()
