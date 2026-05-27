"""Dependency resolution module for the task scheduler.

Resolves job dependencies in processing waves. Each wave resolves
jobs whose dependencies have been satisfied in previous waves.
Wave statistics track the resolution state at each step.
"""

import configparser


class DependencyResolver:
    """Resolves job dependencies in iterative waves.

    Processes jobs in configurable wave sizes and tracks which jobs
    have their dependencies satisfied. Wave statistics report the
    resolution counts at each processing step.
    """

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._wave_size = self._config.getint("execution", "wave_size")

    def resolve(self, ordered_entries):
        """Resolve dependencies across processing waves.

        Returns:
            resolved_plan: list of entries with resolution metadata
            wave_stats: per-stream counts from final processing wave
        """
        resolved_ids = set()
        resolved_plan = []
        wave_stats = {}

        stream_counts = {}

        for i in range(0, len(ordered_entries), self._wave_size):
            wave = ordered_entries[i:i + self._wave_size]
            wave_snapshot = {}

            for entry in wave:
                dep = entry["depends_on"]
                is_resolved = (dep is None) or (dep in resolved_ids)

                resolved_plan.append({
                    "id": entry["id"],
                    "stream_id": entry["stream_id"],
                    "seq_number": entry["seq_number"],
                    "label": entry["label"],
                    "priority_score": entry["priority_score"],
                    "depends_on": entry["depends_on"],
                    "resolved": is_resolved,
                    "wave_index": i // self._wave_size,
                })

                if is_resolved:
                    resolved_ids.add(entry["id"])

                stream = entry["stream_id"]
                if stream not in wave_snapshot:
                    wave_snapshot[stream] = 0
                wave_snapshot[stream] += 1

            # Accumulate across waves
            for stream, count in wave_snapshot.items():
                if stream not in stream_counts:
                    stream_counts[stream] = 0
                stream_counts[stream] += count

        wave_stats = stream_counts
        return resolved_plan, wave_stats

    def get_resolution_summary(self, resolved_plan):
        """Compute summary statistics from the resolved plan."""
        total = len(resolved_plan)
        resolved_count = sum(1 for e in resolved_plan if e["resolved"])
        unresolved_count = total - resolved_count
        streams = set(e["stream_id"] for e in resolved_plan)

        return {
            "total_jobs": total,
            "resolved_count": resolved_count,
            "unresolved_count": unresolved_count,
            "stream_count": len(streams),
            "wave_count": max((e["wave_index"] for e in resolved_plan), default=0) + 1,
        }
