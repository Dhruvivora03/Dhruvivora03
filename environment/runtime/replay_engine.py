"""Replay engine module for the event store.

Replays events in configurable epoch sizes and tracks per-aggregate
event counts at each epoch. Epoch statistics represent the counts
from the most recent processing epoch only.
"""

import configparser


class ReplayEngine:
    """Replays events through the projection system in epochs.

    Processes events in configurable epoch sizes and tracks which
    events have been successfully replayed. Epoch statistics report
    the per-aggregate event counts at each processing step.
    """

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._epoch_size = self._config.getint("replay", "epoch_size")

    @property
    def epoch_size(self):
        return self._epoch_size

    def replay(self, ordered_events):
        """Replay events in epoch-sized batches.

        Returns:
            replay_log: list of entries with replay metadata
            epoch_stats: per-aggregate event counts from final epoch
        """
        replayed = []
        aggregate_totals = {}

        for i in range(0, len(ordered_events), self._epoch_size):
            epoch = ordered_events[i:i + self._epoch_size]
            epoch_snapshot = {}

            for event in epoch:
                replayed.append({
                    "event_id": event["event_id"],
                    "aggregate_id": event["aggregate_id"],
                    "seq_number": event["seq_number"],
                    "event_type": event["event_type"],
                    "payload_value": event["payload_value"],
                    "timestamp": event["timestamp"],
                    "replayed": True,
                    "epoch_index": i // self._epoch_size,
                })

                agg = event["aggregate_id"]
                if agg not in epoch_snapshot:
                    epoch_snapshot[agg] = 0
                epoch_snapshot[agg] += 1

            # Track aggregate counts across epochs
            for agg, count in epoch_snapshot.items():
                if agg not in aggregate_totals:
                    aggregate_totals[agg] = 0
                aggregate_totals[agg] += count

        return replayed, aggregate_totals

    def get_replay_summary(self, replay_log):
        """Compute summary statistics from the replay log."""
        total = len(replay_log)
        replayed_count = sum(1 for e in replay_log if e["replayed"])
        aggregates = set(e["aggregate_id"] for e in replay_log)

        return {
            "total_events": total,
            "replayed_count": replayed_count,
            "failed_count": total - replayed_count,
            "aggregate_count": len(aggregates),
            "epoch_count": max(
                (e["epoch_index"] for e in replay_log), default=0
            ) + 1,
        }
