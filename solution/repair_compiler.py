#!/usr/bin/env python3
"""Repair script for the bytecode compiler.

Analyzes the compiler source code, identifies defects through
inspection of the runtime behavior, and applies targeted fixes.
"""

import os
import sys
import re
import configparser


def analyze_config():
    """Read config.ini and determine correct optimization level section."""
    config = configparser.ConfigParser()
    config.read("/app/runtime/config.ini")
    # The optimizer.passes section has the full pass configuration
    # including the level that enables all passes
    sections = config.sections()
    pass_section = [s for s in sections if "passes" in s]
    if pass_section:
        correct_level = config.getint(pass_section[0], "level")
    else:
        correct_level = 1
    return pass_section[0] if pass_section else "optimizer", correct_level


def fix_source_file_parsing():
    """Detect and fix whitespace handling in source file list parsing.

    Reads the config to find source_files, checks if any entries have
    leading/trailing whitespace, then ensures the compiler strips them.
    """
    config = configparser.ConfigParser()
    config.read("/app/runtime/config.ini")
    raw_sources = config.get("compiler", "source_files")
    entries = raw_sources.split(",")

    # Check if any entries have whitespace issues
    needs_strip = any(e != e.strip() for e in entries)
    if not needs_strip:
        return

    path = "/app/runtime/compiler.py"
    with open(path, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if "raw_sources.split" in line and "strip" not in line:
            # Replace the split without strip with one that strips
            lines[i] = line.replace(
                'set(raw_sources.split(","))',
                'set(s.strip() for s in raw_sources.split(","))'
            )
            break

    with open(path, "w") as f:
        f.writelines(lines)


def fix_optimizer_level_section():
    """Fix the config section used for optimization level.

    Inspects available sections and ensures the optimizer reads from
    the section that contains pass-specific configuration.
    """
    correct_section, _ = analyze_config()

    path = "/app/runtime/optimizer.py"
    with open(path, "r") as f:
        content = f.read()

    # Find the getint call for opt_level and fix the section name
    pattern = r'self\._opt_level\s*=\s*self\._config\.getint\("([^"]+)",\s*"level"\)'
    match = re.search(pattern, content)
    if match and match.group(1) != correct_section:
        old_call = match.group(0)
        new_call = f'self._opt_level = self._config.getint("{correct_section}", "level")'
        content = content.replace(old_call, new_call)

    with open(path, "w") as f:
        f.write(content)


def fix_constant_fold_operands():
    """Fix operand ordering in constant folding.

    In a stack-based VM, for expression 'a OP b':
    - 'a' is pushed first (deeper on stack)
    - 'b' is pushed second (top of stack)
    - The operation should compute a OP b, i.e., first_pushed OP second_pushed

    The _compute function takes (op, left, right) and computes left OP right.
    So it should be called with (op, first_pushed, second_pushed).
    """
    path = "/app/runtime/optimizer.py"
    with open(path, "r") as f:
        content = f.read()

    # Find the _compute call in the constant fold pass
    # The correct call order is first_pushed (left/deeper), second_pushed (right/top)
    if "self._compute(op, second_pushed, first_pushed)" in content:
        content = content.replace(
            "self._compute(op, second_pushed, first_pushed)",
            "self._compute(op, first_pushed, second_pushed)"
        )

    with open(path, "w") as f:
        f.write(content)


def fix_optimizer_isolation():
    """Fix optimizer instance reuse across compilation units.

    The batch compiler must create a fresh optimizer for each file
    to prevent pass statistics from accumulating across units.
    """
    path = "/app/runtime/compiler.py"
    with open(path, "r") as f:
        content = f.read()

    # Check if optimizer is recreated per file in compile_all
    if "self._optimizer = Optimizer(self._config_path)" not in content.split("compile_all")[1].split("def ")[0]:
        # Find the compile loop and add optimizer reset
        # Look for the pattern where compile_file is called without resetting
        compile_loop = re.search(
            r'(            )(unit = self\._compile_file\(filepath, filename\))',
            content
        )
        if compile_loop:
            indent = compile_loop.group(1)
            old_line = compile_loop.group(2)
            new_lines = f"self._optimizer = Optimizer(self._config_path)\n{indent}{old_line}"
            content = content.replace(
                f"{indent}{old_line}",
                f"{indent}{new_lines}",
                1
            )

    with open(path, "w") as f:
        f.write(content)


def fix_variable_name_resolution():
    """Fix case-sensitivity mismatch in variable name resolution.

    The parser normalizes assignment targets to lowercase, but variable
    references in expressions retain their original case. The emitter
    must normalize reference names before symbol table lookup.
    """
    path = "/app/runtime/emitter.py"
    with open(path, "r") as f:
        content = f.read()

    # Check if variable lookup already normalizes
    if "node.name.lower()" in content:
        return

    # Find the VariableRef handling block and add normalization
    # Replace direct node.name usage with normalized lookup
    old_pattern = (
        '        elif isinstance(node, VariableRef):\n'
        '            # Look up variable in symbol table\n'
        '            if node.name in self._symbols:\n'
        '                self._instructions.append(\n'
        '                    Instruction("LOAD_VAR", node.name)\n'
        '                )'
    )
    new_pattern = (
        '        elif isinstance(node, VariableRef):\n'
        '            # Look up variable in symbol table (normalized)\n'
        '            var_name = node.name.lower()\n'
        '            if var_name in self._symbols:\n'
        '                self._instructions.append(\n'
        '                    Instruction("LOAD_VAR", var_name)\n'
        '                )'
    )

    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)

    with open(path, "w") as f:
        f.write(content)


def main():
    """Analyze compiler defects and apply fixes, then re-run."""
    fix_source_file_parsing()
    fix_optimizer_level_section()
    fix_constant_fold_operands()
    fix_optimizer_isolation()
    fix_variable_name_resolution()

    # Re-run compiler with fixed code
    sys.path.insert(0, "/app")
    for key in list(sys.modules.keys()):
        if key.startswith("runtime"):
            del sys.modules[key]
    from runtime.run_compiler import main as run_main
    run_main()


if __name__ == "__main__":
    main()
