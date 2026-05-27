"""Stream loader module for the event store replay engine.

Loads event records from CSV aggregate stream files. Each aggregate
provides a sequence of domain events with versioning and timestamps.

Configuration for materialized projection parameters is defined
in the [projection.materialized] section of the config file.
"""

import csv
import os
import configparser


class StreamLoader:
    """Loads and filters aggregate event streams based on active configuration."""

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._data_dir = os.path.join(
            os.path.dirname(config_path),
            self._config.get("aggregates", "data_dir")
        )
        raw_aggregates = self._config.get("aggregates", "active_aggregates")
        self._active_aggregates = set(raw_aggregates.split(","))

    def load_all_events(self):
        """Load events from all active aggregate stream files.

        Returns a list of event dicts with keys:
            event_id, aggregate_id, seq_number, event_type,
            payload_value, version, timestamp
        """
        events = []
        stream_files = {
            "orders": self._config.get("aggregates", "orders_file"),
            "payments": self._config.get("aggregates", "payments_file"),
            "inventory": self._config.get("aggregates", "inventory_file"),
        }

        for aggregate_name, filename in stream_files.items():
            if aggregate_name not in self._active_aggregates:
                continue
            filepath = os.path.join(self._data_dir, filename)
            if not os.path.exists(filepath):
                continue
            with open(filepath, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    events.append({
                        "event_id": row["event_id"],
                        "aggregate_id": row["aggregate_id"],
                        "seq_number": int(row["seq_number"]),
                        "event_type": row["event_type"],
                        "payload_value": int(row["payload_value"]),
                        "version": int(row["version"]),
                        "timestamp": int(row["timestamp"]),
                    })

        return events
