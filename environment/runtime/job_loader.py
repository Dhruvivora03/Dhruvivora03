"""Job loader module for the task scheduler engine.

Loads job definitions from CSV category files. Each category provides
jobs with priorities, durations, dependencies, and metadata.

Configuration for parallel scheduling parameters is defined
in the [scheduling.parallel] section of the config file.
"""

import csv
import os
import configparser


class JobLoader:
    """Loads and filters job data based on active category configuration."""

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._data_dir = os.path.join(
            os.path.dirname(config_path),
            self._config.get("categories", "data_dir")
        )
        raw_categories = self._config.get("categories", "active_categories")
        self._active_categories = set(raw_categories.split(","))

    def load_all_jobs(self):
        """Load jobs from all active category files.

        Returns a list of job dicts with keys:
            job_id, category_id, priority, duration, depends_on, timestamp, seq
        """
        jobs = []
        category_files = {
            "compute": self._config.get("categories", "compute_file"),
            "io": self._config.get("categories", "io_file"),
            "maintenance": self._config.get("categories", "maintenance_file"),
        }

        for category_name, filename in category_files.items():
            if category_name not in self._active_categories:
                continue
            filepath = os.path.join(self._data_dir, filename)
            if not os.path.exists(filepath):
                continue
            with open(filepath, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    deps_raw = row["depends_on"].strip()
                    deps = [d.strip() for d in deps_raw.split(";")] if deps_raw else []
                    jobs.append({
                        "job_id": row["job_id"],
                        "category_id": row["category_id"],
                        "priority": int(row["priority"]),
                        "duration": int(row["duration"]),
                        "depends_on": deps,
                        "timestamp": int(row["timestamp"]),
                        "seq": int(row["seq"]),
                    })

        return jobs
