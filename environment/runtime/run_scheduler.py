"""Main entry point for the task scheduler engine.

Orchestrates job loading, dependency resolution, execution ordering,
resource computation, and output generation. Results are written as
JSON to the output directory.
"""

import json
import os

from runtime.job_loader import JobLoader
from runtime.scheduler_engine import SchedulerEngine
from runtime.plan_builder import PlanBuilder


def main():
    """Run the task scheduler engine end-to-end."""
    config_path = os.path.join(os.path.dirname(__file__), "config.ini")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Stage 1: Load job definitions
    loader = JobLoader(config_path)
    jobs = loader.load_all_jobs()

    # Stage 2: Resolve execution order
    engine = SchedulerEngine(config_path)
    execution_order = engine.resolve_execution_order(jobs)

    # Stage 3: Compute scheduling metrics
    schedule_metrics = engine.compute_schedule_metrics(execution_order)

    # Stage 4: Compute epoch resource utilization
    epoch_resources = engine.compute_epoch_resources(execution_order)

    # Stage 5: Build and write outputs
    builder = PlanBuilder(execution_order, schedule_metrics, epoch_resources)

    schedule_output = builder.build_schedule_output()
    resource_output = builder.build_resource_output()

    with open(os.path.join(output_dir, "schedule_plan.json"), "w") as f:
        json.dump(schedule_output, f, indent=2)

    with open(os.path.join(output_dir, "resource_report.json"), "w") as f:
        json.dump(resource_output, f, indent=2)


if __name__ == "__main__":
    main()
