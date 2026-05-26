"""Report builder for the merkle verification engine.

Constructs structured output from verification results including
proof ordering, chain statistics, and per-window metrics.
"""


class ReportBuilder:
    """Builds verification report output."""

    def __init__(self, ordered_proofs, verify_ctx, window_metrics):
        self._ordered = ordered_proofs
        self._verify_ctx = verify_ctx
        self._window_metrics = window_metrics

    def build_verification_report(self):
        """Build the main verification report.

        Returns a dict with proof ordering, verification scores,
        and chain summaries.
        """
        proof_order = []
        for proof in self._ordered:
            proof_order.append({
                "proof_id": proof["proof_id"],
                "chain_id": proof["chain_id"],
                "depth": proof["depth"],
                "position": proof["position"],
                "timestamp": proof["timestamp"],
            })

        chain_counts = {}
        for proof in self._ordered:
            chain = proof["chain_id"]
            chain_counts[chain] = chain_counts.get(chain, 0) + 1

        return {
            "proof_order": proof_order,
            "total_proofs": len(self._ordered),
            "verification_scores": self._verify_ctx["scores"],
            "chain_counts": chain_counts,
            "rounds_executed": self._verify_ctx["rounds_executed"],
            "chain_stats": self._verify_ctx["chain_stats"],
        }

    def build_metrics_report(self):
        """Build the metrics report.

        Returns a dict with per-chain window metrics and summary.
        """
        return {
            "window_metrics": self._window_metrics,
            "total_proofs": len(self._ordered),
            "chains_verified": sorted(
                set(p["chain_id"] for p in self._ordered)
            ),
            "verification_coverage": self._compute_coverage(),
        }

    def _compute_coverage(self):
        """Compute verification coverage ratio."""
        scores = self._verify_ctx["scores"]
        if not scores:
            return 0.0
        verified = sum(1 for s in scores.values() if s > 0)
        return round(verified / len(scores), 4)
