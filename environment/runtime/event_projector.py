"""Event projector module for the event store replay engine.

Projects events into materialized views by applying event handlers
in sequence order. Uses configurable snapshot intervals from the
projection configuration section.
"""

import configparser


class EventProjector:
    """Projects events into materialized aggregate state.

    Applies events sequentially to build projection state. Uses
    configurable snapshot interval for checkpoint generation.
    Projection scores are computed using version-weighted values.
    """

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._snapshot_interval = self._config.getint(
            "projection", "snapshot_interval"
        )
        self._projections = {}
        self._event_count = 0

    @property
    def snapshot_interval(self):
        return self._snapshot_interval

    def project_events(self, events):
        """Project a list of events into materialized state.

        Builds per-aggregate projections and computes cumulative
        payload totals with version weighting applied.
        """
        if not events:
            return

        for event in events:
            self._event_count += 1
            agg = event["aggregate_id"]

            if agg not in self._projections:
                self._projections[agg] = {
                    "aggregate_id": agg,
                    "total_payload": 0,
                    "event_count": 0,
                    "last_version": 0,
                    "last_event_type": None,
                    "projection_score": 0.0,
                }

            proj = self._projections[agg]
            proj["total_payload"] += event["payload_value"]
            proj["event_count"] += 1
            proj["last_version"] = event["version"]
            proj["last_event_type"] = event["event_type"]

            # Score uses version-weighted contribution
            weight = event["version"] / max(self._snapshot_interval, 1)
            proj["projection_score"] += round(
                event["payload_value"] * weight, 4
            )

    def get_projections(self):
        """Return all materialized projections."""
        return dict(self._projections)

    def get_ordered_events(self):
        """Return events in their projected execution order."""
        return list(self._projections.values())

    def get_statistics(self):
        """Return projection statistics."""
        if not self._projections:
            return {
                "total_projected": 0,
                "snapshot_interval": self._snapshot_interval,
                "aggregate_count": 0,
            }
        return {
            "total_projected": self._event_count,
            "snapshot_interval": self._snapshot_interval,
            "aggregate_count": len(self._projections),
        }
