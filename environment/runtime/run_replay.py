"""Main entry point for the event store replay engine.

Orchestrates stream loading, event ordering, projection building,
epoch-based replay, and output generation. Results are written as
JSON to the output directory.
"""

import json
import os

from runtime.stream_loader import StreamLoader
from runtime.event_ordering import EventOrderer
from runtime.event_projector import EventProjector
from runtime.replay_engine import ReplayEngine


def main():
    """Run the event store replay engine end-to-end."""
    config_path = os.path.join(os.path.dirname(__file__), "config.ini")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Stage 1: Load aggregate event streams
    loader = StreamLoader(config_path)
    events = loader.load_all_events()

    # Stage 2: Order events deterministically
    orderer = EventOrderer()
    ordered = orderer.order_events(events)

    # Stage 3: Build materialized projections
    projector = EventProjector(config_path)
    projector.project_events(ordered)

    # Stage 4: Replay events in epochs
    engine = ReplayEngine(config_path)
    replay_log, epoch_stats = engine.replay(ordered)

    # Stage 5: Compute summaries
    replay_summary = engine.get_replay_summary(replay_log)
    projection_stats = projector.get_statistics()
    projections = projector.get_projections()

    # Stage 6: Write outputs
    replay_output = {
        "replay_log": replay_log,
        "ordered_events_head": [
            {
                "event_id": e["event_id"],
                "aggregate_id": e["aggregate_id"],
                "event_type": e["event_type"],
                "timestamp": e["timestamp"],
            }
            for e in ordered[:10]
        ],
        "total_events_loaded": len(ordered),
    }

    stats_output = {
        "projection_statistics": projection_stats,
        "replay_summary": replay_summary,
        "epoch_processing_stats": epoch_stats,
        "projections": projections,
        "engine_config": {
            "epoch_size": engine.epoch_size,
            "snapshot_interval": projector.snapshot_interval,
        },
    }

    with open(os.path.join(output_dir, "replay_log.json"), "w") as f:
        json.dump(replay_output, f, indent=2)

    with open(os.path.join(output_dir, "projection_stats.json"), "w") as f:
        json.dump(stats_output, f, indent=2)


if __name__ == "__main__":
    main()
