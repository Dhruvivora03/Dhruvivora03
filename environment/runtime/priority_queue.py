"""Priority queue implementation for deadline-based task scheduling.

Computes priority scores using deadline urgency and base cost,
then maintains a sorted queue for execution ordering. Uses
configurable urgency multiplier from scheduling parameters.
"""

import configparser


class DeadlinePriorityQueue:
    """Priority queue that orders jobs by computed deadline-based scores.

    Priority score is computed as:
        score = urgency_multiplier * (max_deadline - job_deadline) + base_cost

    Higher scores indicate more urgent jobs that should execute first.
    Jobs are sorted in descending priority order for execution.
    """

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._urgency_multiplier = self._config.getfloat(
            "scheduling", "urgency_multiplier"
        )
        self._base_priority = self._config.getint("scheduling", "base_priority")
        self._entries = []
        self._max_deadline = 0

    @property
    def size(self):
        return len(self._entries)

    @property
    def urgency_multiplier(self):
        return self._urgency_multiplier

    def build_queue(self, jobs):
        """Build the priority queue from a list of job records.

        Computes priority scores and sorts jobs for execution.
        """
        if not jobs:
            return

        self._max_deadline = max(j["deadline"] for j in jobs)

        for job in jobs:
            score = self._compute_score(job)
            self._entries.append({
                "id": job["id"],
                "stream_id": job["stream_id"],
                "seq_number": job["seq_number"],
                "label": job["label"],
                "deadline": job["deadline"],
                "base_cost": job["base_cost"],
                "depends_on": job["depends_on"],
                "timestamp": job["timestamp"],
                "priority_score": score,
            })

        # Sort by priority descending for execution order
        # Note: seq_number is local to each stream
        self._entries.sort(
            key=lambda e: (-e["priority_score"], e["seq_number"])
        )

    def _compute_score(self, job):
        """Compute deadline-based priority score for a job."""
        urgency = (self._max_deadline - job["deadline"]) / 1000.0
        score = self._urgency_multiplier * urgency + job["base_cost"]
        return round(score, 4)

    def get_ordered_entries(self):
        """Return all entries in priority execution order."""
        return list(self._entries)

    def get_top_k(self, k):
        """Return the top-k highest priority entries."""
        return list(self._entries[:k])

    def get_statistics(self):
        """Return queue statistics."""
        if not self._entries:
            return {
                "total_enqueued": 0,
                "urgency_multiplier": self._urgency_multiplier,
                "max_deadline": 0,
                "score_range": {"min": 0, "max": 0},
            }
        scores = [e["priority_score"] for e in self._entries]
        return {
            "total_enqueued": len(self._entries),
            "urgency_multiplier": self._urgency_multiplier,
            "max_deadline": self._max_deadline,
            "score_range": {
                "min": round(min(scores), 4),
                "max": round(max(scores), 4),
            },
        }
