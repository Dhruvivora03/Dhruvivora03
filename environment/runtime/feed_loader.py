"""Feed loader module for the spatial indexing engine.

Loads geospatial point data from CSV feed files. Each feed provides
location records with coordinates, labels, and metadata.

Configuration parameters for rtree-specific settings are defined
in the [indexing.rtree] section of the config file.
"""

import csv
import os
import configparser


class FeedLoader:
    """Loads and filters spatial feed data based on active feed configuration."""

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._data_dir = os.path.join(
            os.path.dirname(config_path),
            self._config.get("feeds", "data_dir")
        )
        raw_feeds = self._config.get("feeds", "active_feeds")
        self._active_feeds = set(raw_feeds.split(","))

    def load_all_records(self):
        """Load records from all active feed files.

        Returns a list of record dicts with keys:
            id, feed_id, x, y, label, timestamp, insert_order
        """
        records = []
        feed_files = {
            "sensor": self._config.get("feeds", "sensor_file"),
            "landmark": self._config.get("feeds", "landmark_file"),
            "zone": self._config.get("feeds", "zone_file"),
        }

        for feed_name, filename in feed_files.items():
            if feed_name not in self._active_feeds:
                continue
            filepath = os.path.join(self._data_dir, filename)
            if not os.path.exists(filepath):
                continue
            with open(filepath, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append({
                        "id": row["id"],
                        "feed_id": row["feed_id"],
                        "x": float(row["x"]),
                        "y": float(row["y"]),
                        "label": row["label"],
                        "timestamp": int(row["timestamp"]),
                        "insert_order": int(row["insert_order"]),
                    })

        return records
