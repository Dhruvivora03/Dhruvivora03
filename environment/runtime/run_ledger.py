"""Main entry point for the ledger replay engine.

Orchestrates event loading, sorting, replay, projection building,
and output generation. Results are written as JSON to the output directory.
"""

import json
import os

from runtime.event_loader import EventLoader
from runtime.ledger_engine import LedgerEngine
from runtime.projection_builder import ProjectionBuilder


def main():
    """Run the ledger replay engine end-to-end."""
    config_path = os.path.join(os.path.dirname(__file__), "config.ini")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Stage 1: Load events from streams
    loader = EventLoader(config_path)
    events = loader.load_all_events()

    # Stage 2: Sort events for replay
    engine = LedgerEngine(config_path)
    sorted_events = engine.sort_events(events)

    # Stage 3: Replay events to compute balances
    account_balances, event_counts = engine.replay_events(sorted_events)

    # Stage 4: Compute window projections
    window_projections = engine.compute_window_projections(sorted_events)

    # Stage 5: Build and write outputs
    builder = ProjectionBuilder(
        sorted_events, account_balances, event_counts, window_projections
    )

    ledger_output = builder.build_ledger_output()
    projection_output = builder.build_projection_output()

    with open(os.path.join(output_dir, "ledger_results.json"), "w") as f:
        json.dump(ledger_output, f, indent=2)

    with open(os.path.join(output_dir, "projection_stats.json"), "w") as f:
        json.dump(projection_output, f, indent=2)


if __name__ == "__main__":
    main()
