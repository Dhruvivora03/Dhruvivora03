# Merkle Verifier Repair — Debugging Task

## Overview

A cryptographic merkle proof verification engine loads proof records from multiple hash chains (SHA-256, BLAKE2b, Keccak-256), orders them by tree position for deterministic processing, runs multi-round verification passes computing per-proof confidence scores, and produces verification reports with per-chain metrics across configurable analysis windows.

## System Environment

- **Language**: Python 3.11
- **Runtime**: `/app/runtime/` (source, config, data, output)
- **Global system-wide tooling**: `uv` and `pytest` are available

## Processing Stages

1. **Chain Loading** — Reads CSV proof files from each enabled hash chain. Chain activation is managed by the `ChainRegistry` class which resolves enabled chains from configuration. Each chain provides merkle proof records with leaf hashes, root hashes, tree depths, node positions, and sequencing metadata.

2. **Proof Ordering** — Orders proofs for deterministic verification processing. Proofs are sorted by `(timestamp, position, seq)` where position represents the merkle tree node index, ensuring consistent ordering that respects tree structure when multiple proofs share the same timestamp.

3. **Verification Passes** — Runs the configured number of verification rounds over ordered proofs. Each round computes a SHA-256 based verification hash from the proof metadata and checks it against a depth-scaled threshold. The engine should execute exactly `verification_rounds` iterations (3 rounds per configuration).

4. **Window Metrics** — Computes per-chain metrics within analysis windows. Tracks depth transitions (where current depth >= previous depth) within each window. The final metrics represent the last window state only, not accumulated totals.

5. **Report Generation** — Writes verification results and metrics to JSON files in the output directory.

## Problem

The engine runs without errors but produces incorrect verification results:

- Some hash chains appear to be missing from the verification entirely
- Verification coverage is lower than expected, suggesting insufficient rounds are executed
- Window metrics show zero depth transitions for some chains despite varied proof depths
- Proof ordering shows inconsistencies for proofs sharing the same timestamp

## Expected Correct Output

When all defects are fixed:

- All 55 proofs (20 sha256 + 18 blake2b + 17 keccak256) should be loaded
- Verification should execute exactly 3 rounds, producing coverage of 0.2364 (13/55 verified)
- Window metrics for sha256 in the final window should show depth_transitions=3
- Proofs at the same timestamp should be ordered by (timestamp, position, seq)

## Output Schema

### `/app/runtime/output/verification_report.json`

| Field | Type | Description |
|-------|------|-------------|
| `proof_order` | list | Ordered list of proof metadata objects |
| `proof_order[].proof_id` | string | Unique proof identifier |
| `proof_order[].chain_id` | string | Source hash chain name |
| `proof_order[].depth` | integer | Merkle tree depth |
| `proof_order[].position` | integer | Node position in tree |
| `proof_order[].timestamp` | integer | Proof timestamp |
| `total_proofs` | integer | Total proofs loaded |
| `verification_scores` | object | Per-proof verification score mapping |
| `chain_counts` | object | Number of proofs per chain |
| `chain_counts.sha256` | integer | SHA-256 proof count |
| `chain_counts.blake2b` | integer | BLAKE2b proof count |
| `chain_counts.keccak256` | integer | Keccak-256 proof count |
| `rounds_executed` | integer | Number of verification rounds |
| `chain_stats` | object | Per-chain verification statistics |

### `/app/runtime/output/metrics_report.json`

| Field | Type | Description |
|-------|------|-------------|
| `window_metrics` | object | Per-chain metrics from final analysis window |
| `window_metrics.<chain>.proof_count` | integer | Proofs in final window |
| `window_metrics.<chain>.depth_transitions` | integer | Depth transitions in final window |
| `window_metrics.<chain>.total_depth` | integer | Sum of depths in final window |
| `total_proofs` | integer | Total proofs processed |
| `chains_verified` | list | Sorted list of chain names |
| `verification_coverage` | float | Ratio of verified to total proofs |

## Key Files

| File | Purpose |
|------|---------|
| `/app/runtime/config.ini` | Configuration with chain list, verifier parameters, and metrics settings |
| `/app/runtime/chain_registry.py` | Resolves enabled chains from configuration; filters by active status |
| `/app/runtime/proof_loader.py` | Loads merkle proof records from enabled chain files |
| `/app/runtime/verifier_engine.py` | Orders proofs, runs verification rounds, computes window metrics |
| `/app/runtime/report_builder.py` | Constructs structured output from verification results |
| `/app/runtime/run_verifier.py` | Main entry point orchestrating the full process |
| `/app/runtime/data/sha256_proofs.csv` | SHA-256 merkle proof records (20 entries) |
| `/app/runtime/data/blake2b_proofs.csv` | BLAKE2b merkle proof records (18 entries) |
| `/app/runtime/data/keccak256_proofs.csv` | Keccak-256 merkle proof records (17 entries) |

## Your Task

Identify and fix defects in the runtime source files under `/app/runtime/`. The data files are correct — the bugs are in the Python source code and its interaction with the configuration. Focus on:

- How chain names are resolved from configuration in the registry class
- How many verification rounds are actually executed vs configured
- How depth transitions are detected and how metrics aggregate across windows
- Which field is used for ordering proofs at the same timestamp
