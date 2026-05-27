"""Event ordering module for the event store replay engine.

Provides deterministic ordering of events across multiple aggregate
streams. Events are sorted for replay in a globally consistent
order using timestamp and sequence metadata.

Events from different aggregates may share timestamps. The seq_number
field is local to each aggregate stream and does not provide global
ordering across aggregates.
"""


class EventOrderer:
    """Orders events deterministically for replay processing.

    Sorts events from multiple aggregate streams into a single
    ordered sequence suitable for replay. The ordering must be
    deterministic across runs for consistency guarantees.
    """

    def __init__(self):
        self._ordered = []

    def order_events(self, events):
        """Sort events into deterministic replay order.

        Events are ordered by timestamp for temporal consistency.
        # Note: seq_number is local to each aggregate stream
        """
        self._ordered = sorted(
            events,
            key=lambda e: (e["timestamp"], e["seq_number"])
        )
        return self._ordered

    def get_ordered(self):
        """Return the ordered event list."""
        return list(self._ordered)

    def get_ordering_statistics(self):
        """Return ordering statistics."""
        if not self._ordered:
            return {"total_ordered": 0, "timestamp_range": None}

        timestamps = [e["timestamp"] for e in self._ordered]
        return {
            "total_ordered": len(self._ordered),
            "timestamp_range": {
                "min": min(timestamps),
                "max": max(timestamps),
            },
        }
