"""Main entry point for the deadline task scheduling engine.

Orchestrates stream loading, priority queue construction, dependency
resolution, and output generation. Results are written as JSON to
the output directory.
"""

import json
import os

from runtime.stream_loader import StreamLoader
from runtime.priority_queue import DeadlinePriorityQueue
from runtime.dependency_resolver import DependencyResolver


def main():
    """Run the task scheduler engine end-to-end."""
    config_path = os.path.join(os.path.dirname(__file__), "config.ini")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Stage 1: Load job streams
    loader = StreamLoader(config_path)
    jobs = loader.load_all_jobs()

    # Stage 2: Build priority queue
    queue = DeadlinePriorityQueue(config_path)
    queue.build_queue(jobs)

    # Stage 3: Resolve dependencies
    resolver = DependencyResolver(config_path)
    ordered = queue.get_ordered_entries()
    resolved_plan, wave_stats = resolver.resolve(ordered)

    # Stage 4: Compute summaries
    resolution_summary = resolver.get_resolution_summary(resolved_plan)
    queue_stats = queue.get_statistics()

    # Stage 5: Write outputs
    execution_output = {
        "execution_plan": resolved_plan,
        "top_priority_jobs": [
            {
                "id": e["id"],
                "stream_id": e["stream_id"],
                "label": e["label"],
                "priority_score": e["priority_score"],
            }
            for e in queue.get_top_k(10)
        ],
        "total_jobs_loaded": queue.size,
    }

    stats_output = {
        "queue_statistics": queue_stats,
        "resolution_summary": resolution_summary,
        "wave_processing_stats": wave_stats,
        "execution_config": {
            "wave_size": resolver._wave_size,
            "urgency_multiplier": queue.urgency_multiplier,
        },
    }

    with open(os.path.join(output_dir, "execution_plan.json"), "w") as f:
        json.dump(execution_output, f, indent=2)

    with open(os.path.join(output_dir, "queue_stats.json"), "w") as f:
        json.dump(stats_output, f, indent=2)


if __name__ == "__main__":
    main()
