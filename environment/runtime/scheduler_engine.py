"""Scheduler engine module.

Resolves job dependencies and produces execution schedules using
topological ordering with priority-based tiebreaking. Jobs are
processed in configurable epochs for resource tracking.
"""

import configparser
from collections import deque


class SchedulerEngine:
    """Resolves dependencies and schedules jobs in priority order."""

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._epoch_size = self._config.getint("scheduling", "epoch_size")
        self._max_concurrent = self._config.getint(
            "scheduling", "max_concurrent"
        )

    @property
    def epoch_size(self):
        return self._epoch_size

    @property
    def max_concurrent(self):
        return self._max_concurrent

    def resolve_execution_order(self, jobs):
        """Resolve job execution order using topological sort with priority.

        Jobs are ordered by dependency resolution first, then by priority
        (descending) for jobs at the same dependency depth. For jobs with
        identical priority, ordering uses seq number to break ties.
        """
        # Note: seq is local to each category
        job_map = {j["job_id"]: j for j in jobs}
        in_degree = {j["job_id"]: 0 for j in jobs}
        dependents = {j["job_id"]: [] for j in jobs}

        for job in jobs:
            for dep in job["depends_on"]:
                if dep in job_map:
                    in_degree[job["job_id"]] += 1
                    dependents[dep].append(job["job_id"])

        # Start with jobs that have no dependencies
        ready = []
        for job in jobs:
            if in_degree[job["job_id"]] == 0:
                ready.append(job)

        # Sort ready jobs by priority (desc), then seq for tiebreaking
        ready.sort(key=lambda j: (-j["priority"], j["seq"]))

        execution_order = []
        while ready:
            # Take the highest priority ready job
            current = ready.pop(0)
            execution_order.append(current)

            # Update dependents
            for dep_id in dependents[current["job_id"]]:
                in_degree[dep_id] -= 1
                if in_degree[dep_id] == 0:
                    dep_job = job_map[dep_id]
                    ready.append(dep_job)
                    ready.sort(key=lambda j: (-j["priority"], j["seq"]))

        return execution_order

    def compute_schedule_metrics(self, execution_order):
        """Compute scheduling metrics from the execution order.

        Returns total duration, critical path length, and per-category
        job counts.
        """
        total_duration = sum(j["duration"] for j in execution_order)
        category_counts = {}
        for job in execution_order:
            cat = job["category_id"]
            if cat not in category_counts:
                category_counts[cat] = 0
            category_counts[cat] += 1

        # Compute critical path (longest dependency chain)
        job_map = {j["job_id"]: j for j in execution_order}
        depths = {}
        for job in execution_order:
            if not job["depends_on"] or all(
                d not in job_map for d in job["depends_on"]
            ):
                depths[job["job_id"]] = 1
            else:
                max_dep_depth = 0
                for dep in job["depends_on"]:
                    if dep in depths:
                        max_dep_depth = max(max_dep_depth, depths[dep])
                depths[job["job_id"]] = max_dep_depth + 1

        critical_path = max(depths.values()) if depths else 0

        return {
            "total_duration": total_duration,
            "critical_path_depth": critical_path,
            "category_counts": category_counts,
            "total_jobs_scheduled": len(execution_order),
        }

    def compute_epoch_resources(self, execution_order):
        """Compute per-epoch resource utilization snapshots.

        Processes jobs in epochs of configured size. The final resource
        report should reflect utilization from the last epoch only,
        representing the most recent scheduling state.
        """
        epoch_resources = {}

        for i in range(0, len(execution_order), self._epoch_size):
            epoch = execution_order[i:i + self._epoch_size]
            epoch_snapshot = {}

            for job in epoch:
                cat = job["category_id"]
                if cat not in epoch_snapshot:
                    epoch_snapshot[cat] = 0
                epoch_snapshot[cat] += job["duration"]

            # Accumulate across epochs
            for cat, duration in epoch_snapshot.items():
                if cat not in epoch_resources:
                    epoch_resources[cat] = 0
                epoch_resources[cat] += duration

        return epoch_resources
