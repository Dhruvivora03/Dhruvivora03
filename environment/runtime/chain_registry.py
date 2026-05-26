"""Chain registry for the merkle proof verification engine.

Manages which proof chains are enabled for verification. Chain
activation state is tracked in the configuration registry section
where each chain appears as an individual key with status value.

The [chains.registry] section defines per-chain activation:
    sha256 = active
    blake2b = active
    keccak256 = active
"""

import configparser


class ChainRegistry:
    """Registry of active verification chains.

    Determines which chains participate in verification by reading
    the chain configuration. Active chains are those listed in the
    enabled set resolved from config.
    """

    def __init__(self, config):
        self._config = config
        self._enabled = self._load_enabled_chains()

    def _load_enabled_chains(self):
        """Load the set of enabled chain identifiers.

        Reads chain names from the configuration. Chains listed in
        the config with active status are included in verification.
        """
        # Read enabled chains from the chains section configuration
        raw = self._config.get("chains", "enabled_chains")
        return set(raw.split(","))

    @property
    def enabled_chains(self):
        """Return the set of enabled chain identifiers."""
        return self._enabled

    def is_enabled(self, chain_id):
        """Check if a specific chain is enabled for verification."""
        return chain_id in self._enabled

    def chain_count(self):
        """Return the number of enabled chains."""
        return len(self._enabled)
