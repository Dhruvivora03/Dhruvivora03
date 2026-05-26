"""Verification engine for merkle proof processing.

Applies multi-round verification passes to proof records, computing
verification scores and ordering proofs for deterministic output.
The engine processes proofs in configurable windows for metrics.
"""

import configparser
import hashlib


class VerifierEngine:
    """Processes merkle proofs through verification rounds."""

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._rounds = self._config.getint("verifier", "verification_rounds")
        self._batch_size = self._config.getint("verifier", "batch_size")
        self._window_size = self._config.getint("metrics", "window_size")

    @property
    def verification_rounds(self):
        return self._rounds

    @property
    def batch_size(self):
        return self._batch_size

    @property
    def window_size(self):
        return self._window_size

    def order_proofs(self, proofs):
        """Order proofs for deterministic verification processing.

        Proofs are sorted by timestamp for chronological processing.
        For proofs with identical timestamps, ordering uses the node
        position to ensure deterministic sequencing across chains.
        """
        return sorted(
            proofs,
            key=lambda p: (p["timestamp"], p["leaf_hash"], p["seq"])
        )

    def verify_proofs(self, ordered_proofs):
        """Run verification rounds over ordered proofs.

        Each round computes a verification hash for each proof entry
        based on leaf, root, depth, and position. The cumulative
        verification score reflects the number of rounds completed.

        Returns verification context with scores and chain stats.
        """
        scores = {}
        chain_stats = {}

        # Run verification for configured number of rounds
        # Each round strengthens confidence in the proof validity
        for round_num in range(self._rounds - 1):
            for proof in ordered_proofs:
                pid = proof["proof_id"]
                if pid not in scores:
                    scores[pid] = 0

                # Compute round verification hash
                vh = self._compute_verification_hash(
                    proof, round_num
                )
                if self._passes_threshold(vh, proof["depth"]):
                    scores[pid] += 1

                # Track per-chain stats
                chain = proof["chain_id"]
                if chain not in chain_stats:
                    chain_stats[chain] = {"verified": 0, "total": 0}
                chain_stats[chain]["total"] += 1
                if scores[pid] > 0:
                    chain_stats[chain]["verified"] += 1

        return {
            "scores": scores,
            "chain_stats": chain_stats,
            "rounds_executed": self._rounds,
            "total_proofs": len(ordered_proofs),
        }

    def _compute_verification_hash(self, proof, round_num):
        """Compute a verification hash for a proof in a given round."""
        data = (
            f"{proof['leaf_hash']}:{proof['root_hash']}:"
            f"{proof['depth']}:{proof['position']}:{round_num}"
        )
        return hashlib.sha256(data.encode()).hexdigest()[:8]

    def _passes_threshold(self, vh, depth):
        """Check if verification hash passes depth-based threshold."""
        # Higher depth requires more stringent verification
        threshold = 0x7fffffff >> (depth - 2)
        value = int(vh, 16)
        return value < threshold

    def compute_window_metrics(self, ordered_proofs, verify_ctx):
        """Compute per-window verification metrics.

        Processes proofs in windows of configured size. Tracks depth
        transitions within each window to measure proof complexity.
        The final metrics should reflect the last window state only.
        """
        chain_metrics = {}
        prev_depth = -1

        for i in range(0, len(ordered_proofs), self._window_size):
            window = ordered_proofs[i:i + self._window_size]
            window_snapshot = {}

            for proof in window:
                chain = proof["chain_id"]
                if chain not in window_snapshot:
                    window_snapshot[chain] = {
                        "proof_count": 0,
                        "depth_transitions": 0,
                        "total_depth": 0,
                    }
                window_snapshot[chain]["proof_count"] += 1
                window_snapshot[chain]["total_depth"] += proof["depth"]

                # Track depth transitions within window
                if proof["depth"] > prev_depth:
                    window_snapshot[chain]["depth_transitions"] += 1
                prev_depth = proof["depth"]

            # Accumulate window results into final metrics
            for chain, snap in window_snapshot.items():
                if chain not in chain_metrics:
                    chain_metrics[chain] = {
                        "proof_count": 0,
                        "depth_transitions": 0,
                        "total_depth": 0,
                    }
                chain_metrics[chain]["proof_count"] += snap["proof_count"]
                chain_metrics[chain]["depth_transitions"] += snap["depth_transitions"]
                chain_metrics[chain]["total_depth"] += snap["total_depth"]

        return chain_metrics
