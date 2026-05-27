"""Event store module for the replay engine.

Stores events and provides ordered replay sequences with snapshot
support. Events are stored per-stream and can be replayed in
deterministic global order for projection building.
"""

import configparser


class EventStore:
    """Append-only event store with snapshot support.

    Events are stored in insertion order and can be replayed as a
    deterministic global sequence. Snapshots are created at
    configurable intervals for checkpoint/recovery support.
    """

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._snapshot_interval = self._config.getint(
            "projection", "snapshot_interval"
        )
        self._events = []
        self._stream_counts = {}
        self._snapshot_count = 0

    @property
    def size(self):
        return len(self._events)

    @property
    def snapshot_interval(self):
        return self._snapshot_interval

    @property
    def snapshot_count(self):
        return self._snapshot_count

    def append(self, event):
        """Append an event to the store."""
        self._events.append(event)
        stream = event["stream_id"]
        if stream not in self._stream_counts:
            self._stream_counts[stream] = 0
        self._stream_counts[stream] += 1

        # Create snapshot at configured intervals
        if len(self._events) % self._snapshot_interval == 0:
            self._snapshot_count += 1

    def get_replay_sequence(self):
        """Get all events in deterministic replay order.

        Events are ordered by timestamp for global consistency.
        For events with identical timestamps, ordering uses
        sequence_number for determinism.
        """
        # Note: sequence_number is local to each stream
        return sorted(
            self._events,
            key=lambda e: (e["timestamp"], e["sequence_number"])
        )

    def get_stream_counts(self):
        """Return event counts per stream."""
        return dict(self._stream_counts)

    def get_events_for_stream(self, stream_id):
        """Get all events for a specific stream."""
        return [e for e in self._events if e["stream_id"] == stream_id]
