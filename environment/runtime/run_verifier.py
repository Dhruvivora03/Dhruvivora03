"""Main entry point for the merkle proof verification engine.

Orchestrates proof loading, ordering, verification pass execution,
metrics computation, and report generation.
"""

import json
import os

from runtime.proof_loader import ProofLoader
from runtime.verifier_engine import VerifierEngine
from runtime.report_builder import ReportBuilder


def main():
    """Run the merkle verification engine end-to-end."""
    config_path = os.path.join(os.path.dirname(__file__), "config.ini")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Stage 1: Load proof records from chains
    loader = ProofLoader(config_path)
    proofs = loader.load_all_proofs()

    # Stage 2: Order proofs for processing
    engine = VerifierEngine(config_path)
    ordered = engine.order_proofs(proofs)

    # Stage 3: Run verification passes
    verify_ctx = engine.verify_proofs(ordered)

    # Stage 4: Compute window metrics
    window_metrics = engine.compute_window_metrics(ordered, verify_ctx)

    # Stage 5: Build and write outputs
    builder = ReportBuilder(ordered, verify_ctx, window_metrics)

    verification_report = builder.build_verification_report()
    metrics_report = builder.build_metrics_report()

    with open(os.path.join(output_dir, "verification_report.json"), "w") as f:
        json.dump(verification_report, f, indent=2)

    with open(os.path.join(output_dir, "metrics_report.json"), "w") as f:
        json.dump(metrics_report, f, indent=2)


if __name__ == "__main__":
    main()
