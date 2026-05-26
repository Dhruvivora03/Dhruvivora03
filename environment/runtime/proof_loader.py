"""Proof loader module for the merkle verification engine.

Loads merkle proof records from CSV chain files. Each chain provides
proof entries with leaf hashes, root hashes, tree depths, node
positions, and verification metadata.
"""

import csv
import os
import configparser

from runtime.chain_registry import ChainRegistry


class ProofLoader:
    """Loads merkle proof data from active chain files."""

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._data_dir = os.path.join(
            os.path.dirname(config_path),
            self._config.get("chains", "data_dir")
        )
        self._registry = ChainRegistry(self._config)

    @property
    def registry(self):
        return self._registry

    def load_all_proofs(self):
        """Load proof records from all enabled chain files.

        Returns a list of proof dicts with keys:
            proof_id, chain_id, leaf_hash, root_hash, depth,
            position, sibling_count, timestamp, seq
        """
        proofs = []
        chain_files = {
            "sha256": self._config.get("chains", "sha256_file"),
            "blake2b": self._config.get("chains", "blake2b_file"),
            "keccak256": self._config.get("chains", "keccak256_file"),
        }

        for chain_name, filename in chain_files.items():
            if not self._registry.is_enabled(chain_name):
                continue
            filepath = os.path.join(self._data_dir, filename)
            if not os.path.exists(filepath):
                continue
            with open(filepath, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    proofs.append({
                        "proof_id": row["proof_id"],
                        "chain_id": row["chain_id"],
                        "leaf_hash": row["leaf_hash"],
                        "root_hash": row["root_hash"],
                        "depth": int(row["depth"]),
                        "position": int(row["position"]),
                        "sibling_count": int(row["sibling_count"]),
                        "timestamp": int(row["timestamp"]),
                        "seq": int(row["seq"]),
                    })

        return proofs
