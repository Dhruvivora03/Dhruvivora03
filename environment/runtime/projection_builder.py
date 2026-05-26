"""Projection builder module.

Constructs the final output projections from replay results,
including event ordering metadata and per-stream statistics.
"""


class ProjectionBuilder:
    """Builds structured output projections from replay results."""

    def __init__(self, sorted_events, account_balances, event_counts,
                 window_projections):
        self._sorted_events = sorted_events
        self._account_balances = account_balances
        self._event_counts = event_counts
        self._window_projections = window_projections

    def build_ledger_output(self):
        """Build the main ledger output structure.

        Returns a dict with replay results, event ordering, and
        account summaries.
        """
        event_order = []
        for event in self._sorted_events:
            event_order.append({
                "event_id": event["event_id"],
                "stream_id": event["stream_id"],
                "account_id": event["account_id"],
                "amount": event["amount"],
                "timestamp": event["timestamp"],
            })

        account_summaries = []
        for acct_id in sorted(self._account_balances.keys()):
            account_summaries.append({
                "account_id": acct_id,
                "final_balance": self._account_balances[acct_id],
            })

        return {
            "event_order": event_order,
            "account_summaries": account_summaries,
            "total_events_replayed": len(self._sorted_events),
            "event_counts_by_stream": self._event_counts,
        }

    def build_projection_output(self):
        """Build the projection statistics output.

        Returns a dict with window projection data and stream metadata.
        """
        return {
            "window_projections": self._window_projections,
            "total_events": len(self._sorted_events),
            "streams_processed": list(
                sorted(set(e["stream_id"] for e in self._sorted_events))
            ),
            "accounts_active": sorted(self._window_projections.keys()),
        }
