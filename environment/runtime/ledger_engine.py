"""Ledger replay engine module.

Replays sorted events through configurable processing windows and
produces account balance projections. Events are ordered by timestamp
with deterministic tiebreaking for concurrent events.
"""

import configparser


class LedgerEngine:
    """Replays events in windows and computes account projections."""

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._window_size = self._config.getint("replay", "window_size")

    @property
    def window_size(self):
        return self._window_size

    def sort_events(self, events):
        """Sort events for deterministic replay ordering.

        Events are ordered by timestamp for chronological replay.
        For events with identical timestamps, ordering uses seq number
        to break ties.
        """
        # Note: seq is local to each stream
        return sorted(events, key=lambda e: (e["timestamp"], e["seq"]))

    def replay_events(self, sorted_events):
        """Replay sorted events and produce per-account balances.

        Processes events in configurable windows. Returns the ledger
        state with account balances and event counts.
        """
        account_balances = {}
        event_counts = {"payments": 0, "refunds": 0, "adjustments": 0}

        for event in sorted_events:
            acct = event["account_id"]
            if acct not in account_balances:
                account_balances[acct] = 0.0
            account_balances[acct] += event["amount"]
            stream = event["stream_id"]
            if stream in event_counts:
                event_counts[stream] += 1

        # Round balances
        for acct in account_balances:
            account_balances[acct] = round(account_balances[acct], 2)

        return account_balances, event_counts

    def compute_window_projections(self, sorted_events):
        """Compute per-window balance snapshots for each account.

        Processes events in windows of configured size. The final
        projection should reflect balances from the last window only,
        representing the most recent state snapshot.
        """
        account_projections = {}

        for i in range(0, len(sorted_events), self._window_size):
            window = sorted_events[i:i + self._window_size]
            window_balances = {}

            for event in window:
                acct = event["account_id"]
                if acct not in window_balances:
                    window_balances[acct] = 0.0
                window_balances[acct] += event["amount"]

            # Round window balances
            for acct in window_balances:
                window_balances[acct] = round(window_balances[acct], 2)

            # Accumulate across windows
            for acct, balance in window_balances.items():
                if acct not in account_projections:
                    account_projections[acct] = 0.0
                account_projections[acct] += balance

        # Round final projections
        for acct in account_projections:
            account_projections[acct] = round(account_projections[acct], 2)

        return account_projections
