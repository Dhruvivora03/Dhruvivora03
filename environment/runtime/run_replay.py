"""Main entry point for the event store replay engine.

Orchestrates stream loading, event store population, projection
building, and output generation. Results are written as JSON to
the output directory.
"""

import json
import os

from runtime.stream_loader import StreamLoader
from runtime.event_store import EventStore
from runtime.projection_engine import ProjectionEngine


def main():
    """Run the event store replay engine end-to-end."""
    config_path = os.path.join(os.path.dirname(__file__), "config.ini")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Stage 1: Load event streams
    loader = StreamLoader(config_path)
    events = loader.load_all_streams()

    # Stage 2: Populate event store
    store = EventStore(config_path)
    for event in events:
        store.append(event)

    # Stage 3: Build replay ordering
    ordered_events = store.get_replay_sequence()

    # Stage 4: Build projections
    engine = ProjectionEngine(config_path, store)
    projection_results = engine.build_projections(ordered_events)
    window_aggregates = engine.compute_window_aggregates(ordered_events)

    # Stage 5: Write outputs
    projection_output = {
        "replay_sequence": [
            {
                "event_id": e["event_id"],
                "stream_id": e["stream_id"],
                "event_type": e["event_type"],
                "timestamp": e["timestamp"],
                "sequence_number": e["sequence_number"],
                "payload_amount": e["payload_amount"],
            }
            for e in ordered_events
        ],
        "projections": projection_results,
        "total_events_replayed": store.size,
    }

    store_stats = {
        "total_events": store.size,
        "snapshot_interval": store.snapshot_interval,
        "snapshots_created": store.snapshot_count,
        "stream_counts": store.get_stream_counts(),
        "window_aggregates": window_aggregates,
        "replay_checksum": engine.compute_checksum(ordered_events),
    }

    with open(os.path.join(output_dir, "projection_results.json"), "w") as f:
        json.dump(projection_output, f, indent=2)

    with open(os.path.join(output_dir, "store_stats.json"), "w") as f:
        json.dump(store_stats, f, indent=2)


if __name__ == "__main__":
    main()
