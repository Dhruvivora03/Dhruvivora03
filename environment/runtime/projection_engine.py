"""Projection engine module.

Builds materialized views from replayed event sequences. Computes
per-window aggregate statistics across configurable replay windows.
"""

import configparser
import hashlib
import json


class ProjectionEngine:
    """Builds projections from event replay sequences in windows."""

    def __init__(self, config_path, store):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._store = store
        self._window_size = self._config.getint("replay", "window_size")

    def build_projections(self, ordered_events):
        """Build materialized view projections from ordered events.

        Groups events by entity_id and computes running totals
        for each entity based on event payloads.
        """
        entity_projections = {}

        for event in ordered_events:
            entity = event["entity_id"]
            if entity not in entity_projections:
                entity_projections[entity] = {
                    "entity_id": entity,
                    "stream_id": event["stream_id"],
                    "event_count": 0,
                    "total_amount": 0.0,
                    "last_event_type": "",
                    "last_timestamp": 0,
                }
            proj = entity_projections[entity]
            proj["event_count"] += 1
            proj["total_amount"] += event["payload_amount"]
            proj["last_event_type"] = event["event_type"]
            proj["last_timestamp"] = event["timestamp"]

        return list(entity_projections.values())

    def compute_window_aggregates(self, ordered_events):
        """Compute per-stream event counts in replay windows.

        Processes events in configurable window sizes and computes
        per-stream counts for each window. The final aggregates
        should reflect the counts from the last window processed.
        """
        stream_totals = {}

        for i in range(0, len(ordered_events), self._window_size):
            window = ordered_events[i:i + self._window_size]
            window_snapshot = {}

            for event in window:
                stream = event["stream_id"]
                if stream not in window_snapshot:
                    window_snapshot[stream] = 0
                window_snapshot[stream] += 1

            # Accumulate across windows
            for stream, count in window_snapshot.items():
                if stream not in stream_totals:
                    stream_totals[stream] = 0
                stream_totals[stream] += count

        return stream_totals

    def compute_checksum(self, ordered_events):
        """Compute a deterministic checksum of the replay sequence.

        Uses event_id ordering to produce a repeatable hash that
        validates the correctness of replay ordering.
        """
        hasher = hashlib.md5()
        for event in ordered_events:
            hasher.update(event["event_id"].encode("utf-8"))
        return hasher.hexdigest()
