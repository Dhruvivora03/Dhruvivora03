"""Event loader module for the ledger replay engine.

Loads transaction events from CSV stream files. Each stream provides
events with account identifiers, amounts, timestamps, and sequence
numbers local to that stream.

Configuration for streaming-specific replay parameters is defined
in the [replay.streaming] section of the config file.
"""

import csv
import os
import configparser


class EventLoader:
    """Loads and filters event data based on active stream configuration."""

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._data_dir = os.path.join(
            os.path.dirname(config_path),
            self._config.get("streams", "data_dir")
        )
        raw_streams = self._config.get("streams", "active_streams")
        self._active_streams = set(raw_streams.split(","))

    def load_all_events(self):
        """Load events from all active stream files.

        Returns a list of event dicts with keys:
            event_id, stream_id, account_id, amount, timestamp, seq
        """
        events = []
        stream_files = {
            "payments": self._config.get("streams", "payments_file"),
            "refunds": self._config.get("streams", "refunds_file"),
            "adjustments": self._config.get("streams", "adjustments_file"),
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
                        "account_id": row["account_id"],
                        "amount": float(row["amount"]),
                        "timestamp": int(row["timestamp"]),
                        "seq": int(row["seq"]),
                    })

        return events
