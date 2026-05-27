#!/usr/bin/env python3
"""Repair script for the bytecode compiler.

Patches four defects in the runtime source code and re-runs the compiler
to produce correct output.
"""

import os
import sys


def patch_source_file_parsing():
    """Fix: strip whitespace from comma-separated source file list."""
    path = "/app/runtime/compiler.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'self._source_files = set(raw_sources.split(","))',
        'self._source_files = set(s.strip() for s in raw_sources.split(","))'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_optimizer_config_section():
    """Fix: read optimization level from correct config section."""
    path = "/app/runtime/optimizer.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        'self._opt_level = self._config.getint("optimizer", "level")',
        'self._opt_level = self._config.getint("optimizer.passes", "level")'
    )
    with open(path, "w") as f:
        f.write(content)


def patch_constant_fold_operand_order():
    """Fix: correct operand order in constant folding computation."""
    path = "/app/runtime/optimizer.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        "folded = self._compute(op, second_pushed, first_pushed)",
        "folded = self._compute(op, first_pushed, second_pushed)"
    )
    with open(path, "w") as f:
        f.write(content)


def patch_optimizer_stats_accumulation():
    """Fix: create fresh optimizer per file to prevent stats accumulation."""
    path = "/app/runtime/compiler.py"
    with open(path, "r") as f:
        content = f.read()
    content = content.replace(
        "            unit = self._compile_file(filepath, filename)\n            self._units.append(unit)",
        "            self._optimizer = Optimizer(self._config_path)\n            unit = self._compile_file(filepath, filename)\n            self._units.append(unit)"
    )
    with open(path, "w") as f:
        f.write(content)


def patch_variable_reference_case():
    """Fix: normalize variable name case in emitter lookup and emission."""
    path = "/app/runtime/emitter.py"
    with open(path, "r") as f:
        content = f.read()
    old_block = '''        elif isinstance(node, VariableRef):
            # Look up variable in symbol table
            if node.name in self._symbols:
                self._instructions.append(
                    Instruction("LOAD_VAR", node.name)
                )
            else:
                # Variable not in symbol table, use default
                self._instructions.append(
                    Instruction("PUSH_CONST", 0)
                )'''
    new_block = '''        elif isinstance(node, VariableRef):
            # Look up variable in symbol table (normalized)
            var_name = node.name.lower()
            if var_name in self._symbols:
                self._instructions.append(
                    Instruction("LOAD_VAR", var_name)
                )
            else:
                # Variable not in symbol table, use default
                self._instructions.append(
                    Instruction("PUSH_CONST", 0)
                )'''
    content = content.replace(old_block, new_block)
    with open(path, "w") as f:
        f.write(content)


def main():
    """Apply all patches and re-run the compiler."""
    patch_source_file_parsing()
    patch_optimizer_config_section()
    patch_constant_fold_operand_order()
    patch_optimizer_stats_accumulation()
    patch_variable_reference_case()

    # Re-run compiler with fixed code
    sys.path.insert(0, "/app")
    for key in list(sys.modules.keys()):
        if key.startswith("runtime"):
            del sys.modules[key]
    from runtime.run_compiler import main as run_main
    run_main()


if __name__ == "__main__":
    main()
