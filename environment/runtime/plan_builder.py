"""Plan builder module.

Constructs the final execution plan output from scheduling results,
including job ordering metadata and resource utilization reports.
"""


class PlanBuilder:
    """Builds structured output from scheduler results."""

    def __init__(self, execution_order, schedule_metrics, epoch_resources):
        self._execution_order = execution_order
        self._schedule_metrics = schedule_metrics
        self._epoch_resources = epoch_resources

    def build_schedule_output(self):
        """Build the main schedule output structure.

        Returns a dict with execution plan, job ordering, and
        scheduling metrics.
        """
        job_plan = []
        for idx, job in enumerate(self._execution_order):
            job_plan.append({
                "position": idx + 1,
                "job_id": job["job_id"],
                "category_id": job["category_id"],
                "priority": job["priority"],
                "duration": job["duration"],
                "depends_on": job["depends_on"],
            })

        return {
            "execution_plan": job_plan,
            "total_jobs_scheduled": self._schedule_metrics["total_jobs_scheduled"],
            "total_duration": self._schedule_metrics["total_duration"],
            "critical_path_depth": self._schedule_metrics["critical_path_depth"],
            "category_counts": self._schedule_metrics["category_counts"],
        }

    def build_resource_output(self):
        """Build the resource utilization output.

        Returns a dict with epoch resource data and scheduling metadata.
        """
        return {
            "epoch_resources": self._epoch_resources,
            "total_jobs": len(self._execution_order),
            "categories_scheduled": sorted(
                set(j["category_id"] for j in self._execution_order)
            ),
        }
