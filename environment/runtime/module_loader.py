"""Module loader for the IR optimization engine.

Loads intermediate representation instruction streams from CSV module
files. Each module provides IR instructions with opcodes, operands,
basic block assignments, and sequencing metadata.

The optimization pass configuration (depth, thresholds) is specified
in the [optimizer.passes] section of the config file.
"""

import csv
import os
import configparser


class ModuleRegistry:
    """Manages the set of active IR modules for optimization."""

    def __init__(self, config):
        self._config = config
        self._active = self._resolve_active_modules()

    def _resolve_active_modules(self):
        """Resolve which modules are active from config."""
        raw = self._config.get("modules", "active_modules")
        return set(raw.split(","))

    @property
    def active_modules(self):
        return self._active

    def is_active(self, module_name):
        return module_name in self._active


class ModuleLoader:
    """Loads IR instruction data from active module files."""

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._data_dir = os.path.join(
            os.path.dirname(config_path),
            self._config.get("modules", "data_dir")
        )
        self._registry = ModuleRegistry(self._config)

    @property
    def registry(self):
        return self._registry

    def load_all_instructions(self):
        """Load instructions from all active module files.

        Returns a list of instruction dicts with keys:
            instr_id, module_id, opcode, dest, src1, src2,
            block_id, timestamp, seq
        """
        instructions = []
        module_files = {
            "arithmetic": self._config.get("modules", "arithmetic_file"),
            "control_flow": self._config.get("modules", "control_flow_file"),
            "memory_ops": self._config.get("modules", "memory_ops_file"),
        }

        for module_name, filename in module_files.items():
            if not self._registry.is_active(module_name):
                continue
            filepath = os.path.join(self._data_dir, filename)
            if not os.path.exists(filepath):
                continue
            with open(filepath, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    instructions.append({
                        "instr_id": row["instr_id"],
                        "module_id": row["module_id"],
                        "opcode": row["opcode"],
                        "dest": row["dest"],
                        "src1": row["src1"],
                        "src2": row["src2"],
                        "block_id": row["block_id"],
                        "timestamp": int(row["timestamp"]),
                        "seq": int(row["seq"]),
                    })

        return instructions
