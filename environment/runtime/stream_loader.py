"""Stream loader module for the task scheduling engine.

Loads job definitions from CSV stream files. Each stream provides
job records with deadlines, costs, dependencies, and ordering metadata.

Configuration for deadline-specific scheduling parameters is defined
in the [scheduling.deadline] section of the config file.
"""

import csv
import os
import configparser


class StreamLoader:
    """Loads and filters job stream data based on active stream configuration."""

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._data_dir = os.path.join(
            os.path.dirname(config_path),
            self._config.get("streams", "data_dir")
        )
        raw_streams = self._config.get("streams", "active_streams")
        self._active_streams = set(raw_streams.split(","))

    def load_all_jobs(self):
        """Load jobs from all active stream files.

        Returns a list of job dicts with keys:
            id, stream_id, seq_number, label, deadline, base_cost,
            depends_on, timestamp
        """
        jobs = []
        stream_files = {
            "compute": self._config.get("streams", "compute_file"),
            "io": self._config.get("streams", "io_file"),
            "network": self._config.get("streams", "network_file"),
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
                    jobs.append({
                        "id": row["id"],
                        "stream_id": row["stream_id"],
                        "seq_number": int(row["seq_number"]),
                        "label": row["label"],
                        "deadline": int(row["deadline"]),
                        "base_cost": int(row["base_cost"]),
                        "depends_on": row["depends_on"] if row["depends_on"] else None,
                        "timestamp": int(row["timestamp"]),
                    })

        return jobs
