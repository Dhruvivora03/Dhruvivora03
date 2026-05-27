"""Stream loader module for the event store replay engine.

Loads event data from CSV stream files. Each stream provides
domain events with timestamps, sequence numbers, and payload data.

Configuration parameters for incremental projection settings are
defined in the [projection.incremental] section of the config file.
"""

import csv
import os
import configparser


class StreamLoader:
    """Loads and filters event stream data based on active stream configuration."""

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._data_dir = os.path.join(
            os.path.dirname(config_path),
            self._config.get("streams", "data_dir")
        )
        raw_streams = self._config.get("streams", "active_streams")
        self._active_streams = set(raw_streams.split(","))

    def load_all_streams(self):
        """Load events from all active stream files.

        Returns a list of event dicts with keys:
            event_id, stream_id, event_type, timestamp,
            sequence_number, payload_amount, entity_id
        """
        events = []
        stream_files = {
            "orders": self._config.get("streams", "orders_file"),
            "payments": self._config.get("streams", "payments_file"),
            "inventory": self._config.get("streams", "inventory_file"),
        }

        for stream_name, filename in stream_files.items():
            if stream_name not in self._active_streams:
                continue
            filepath = os.path.join(self._data_dir, filename)
            if not os.path.exists(filepath):
                continue
            with open(filepath, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    events.append({
                        "event_id": row["event_id"],
                        "stream_id": row["stream_id"],
                        "event_type": row["event_type"],
                        "timestamp": int(row["timestamp"]),
                        "sequence_number": int(row["sequence_number"]),
                        "payload_amount": float(row["payload_amount"]),
                        "entity_id": row["entity_id"],
                    })

        return events
