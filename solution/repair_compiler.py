#!/usr/bin/env python3
"""Repair script for the bytecode compiler.

Diagnoses defects by running the compiler, analyzing output against
expected behavior, tracing root causes through the source code,
and applying computed fixes.
"""

import os
import sys
import re
import ast
import configparser
import importlib


def load_config():
    """Load and return the compiler configuration."""
    config = configparser.ConfigParser()
    config.read("/app/runtime/config.ini")
    return config


def count_source_files(config):
    """Count how many source files should be compiled based on config."""
    raw = config.get("compiler", "source_files")
    return len([s.strip() for s in raw.split(",") if s.strip()])


def detect_whitespace_in_config(config):
    """Detect if config lists have entries with leading/trailing spaces."""
    raw = config.get("compiler", "source_files")
    entries = raw.split(",")
    return any(e != e.strip() for e in entries)


def find_correct_opt_level(config):
    """Determine the correct optimization level by examining all sections.

    Looks for sections that define pass-specific configuration and
    returns the level that enables the standard passes without triggering
    experimental or unsafe optimizations.
    """
    candidate_sections = []
    for section in config.sections():
        if config.has_option(section, "level"):
            level = config.getint(section, "level")
            # Skip sections with experimental/unsafe options
            if (config.has_option(section, "unsafe_elision") or
                config.has_option(section, "speculative_execution")):
                continue
            # Look for sections with standard pass configuration
            if (config.has_option(section, "constant_fold") or
                config.has_option(section, "peephole") or
                "pass" in section):
                candidate_sections.append((section, level))

    if candidate_sections:
        # Pick the section with standard pass options
        best = max(candidate_sections, key=lambda x: x[1])
        return best[0], best[1]
    return "optimizer", 1


def diagnose_constant_fold():
    """Diagnose constant folding by testing a known expression.

    Compiles '10 - 5' and checks if the result is 5 (correct) or -5 (reversed).
    This determines if operand order is swapped.
    """
    sys.path.insert(0, "/app")
    # Clear cached modules
    for key in list(sys.modules.keys()):
        if key.startswith("runtime"):
            del sys.modules[key]

    from runtime.parser import Parser
    from runtime.emitter import BytecodeEmitter
    from runtime.optimizer import Optimizer

    parser = Parser()
    stmts = parser.parse("result = 10 - 3\n")
    symbols = parser.symbol_table
    emitter = BytecodeEmitter(symbols)
    raw = emitter.emit_program(stmts)

    # Create optimizer with high level to test folding
    config = load_config()
    _, correct_level = find_correct_opt_level(config)

    # Use a temp config path to test
    opt = Optimizer("/app/runtime/config.ini")
    optimized = opt.optimize(list(raw))

    # Find the folded constant
    for instr in optimized:
        if instr.opcode == "PUSH_CONST" and isinstance(instr.operand, (int, float)):
            if instr.operand == 7:
                return False  # correct: 10-3=7
            elif instr.operand == -7:
                return True  # reversed operands: 3-10=-7

    return True  # assume reversed if no clear result


def diagnose_variable_resolution():
    """Check if uppercase variable references resolve correctly.

    Parses 'X = 5' followed by 'Y = X + 1' and checks if X resolves
    to LOAD_VAR or falls back to PUSH_CONST 0.
    """
    for key in list(sys.modules.keys()):
        if key.startswith("runtime"):
            del sys.modules[key]

    from runtime.parser import Parser
    from runtime.emitter import BytecodeEmitter

    parser = Parser()
    stmts = parser.parse("X = 5\nY = X + 1\n")
    symbols = parser.symbol_table
    emitter = BytecodeEmitter(symbols)
    bytecode = emitter.emit_program(stmts)

    # Check if X reference emits LOAD_VAR or PUSH_CONST 0
    for instr in bytecode:
        if instr.opcode == "LOAD_VAR":
            return False  # resolves correctly
    return True  # broken: fell through to PUSH_CONST 0


def apply_whitespace_fix():
    """Apply fix: strip whitespace from source file list parsing."""
    path = "/app/runtime/compiler.py"
    with open(path, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if "raw_sources.split" in line and "strip" not in line:
            lines[i] = line.replace(
                'set(raw_sources.split(","))',
                'set(s.strip() for s in raw_sources.split(","))'
            )
            break

    with open(path, "w") as f:
        f.writelines(lines)


def apply_opt_level_fix(correct_section):
    """Apply fix: use the correct config section for optimization level."""
    path = "/app/runtime/optimizer.py"
    with open(path, "r") as f:
        content = f.read()

    pattern = r'self\._opt_level\s*=\s*self\._config\.getint\("([^"]+)",\s*"level"\)'
    match = re.search(pattern, content)
    if match and match.group(1) != correct_section:
        old_call = match.group(0)
        new_call = f'self._opt_level = self._config.getint("{correct_section}", "level")'
        content = content.replace(old_call, new_call)
        with open(path, "w") as f:
            f.write(content)


def apply_operand_order_fix():
    """Apply fix: correct the operand order in constant fold computation.

    The stack pushes left operand first (deeper) and right operand second (top).
    For 'a - b', left=a, right=b. Computation should be a-b,
    so _compute must receive (op, left, right).
    """
    path = "/app/runtime/optimizer.py"
    with open(path, "r") as f:
        content = f.read()

    # Find the _compute call and check argument order
    match = re.search(
        r'folded\s*=\s*self\._compute\(op,\s*(\w+),\s*(\w+)\)',
        content
    )
    if match:
        arg1, arg2 = match.group(1), match.group(2)
        # Correct order: left (first pushed), right (second pushed)
        if arg1 == "right" and arg2 == "left":
            content = content.replace(
                match.group(0),
                "folded = self._compute(op, left, right)"
            )
            with open(path, "w") as f:
                f.write(content)


def apply_optimizer_isolation_fix():
    """Apply fix: ensure optimizer state is fresh for each compilation unit.

    Detects if the optimizer is shared across files by checking the
    compile_all method for per-file reinitialization.
    """
    path = "/app/runtime/compiler.py"
    with open(path, "r") as f:
        content = f.read()

    # Extract the compile_all method body
    compile_all_section = content.split("def compile_all")[1].split("\n    def ")[0]

    # Check if optimizer is already reset per file
    if "Optimizer(self._config_path)" in compile_all_section:
        return

    # Find where _compile_file is called and insert optimizer reset before it
    match = re.search(
        r'(            )(unit = self\._compile_file\(filepath, filename\))',
        content
    )
    if match:
        indent = match.group(1)
        old_line = match.group(2)
        new_block = f"self._optimizer = Optimizer(self._config_path)\n{indent}{old_line}"
        content = content.replace(
            f"{indent}{old_line}",
            f"{indent}{new_block}",
            1
        )
        with open(path, "w") as f:
            f.write(content)


def apply_variable_resolution_fix():
    """Apply fix: normalize variable references to match symbol table case.

    The parser stores symbols in lowercase, so the emitter must convert
    variable reference names to lowercase before lookup.
    """
    path = "/app/runtime/emitter.py"
    with open(path, "r") as f:
        content = f.read()

    if "node.name.lower()" in content:
        return  # already fixed

    # Locate the VariableRef branch in _emit_expr
    # Replace the direct name lookup with normalized lookup
    old_block = (
        '            if node.name in self._symbols:\n'
        '                self._instructions.append(\n'
        '                    Instruction("LOAD_VAR", node.name)\n'
        '                )'
    )
    new_block = (
        '            var_name = node.name.lower()\n'
        '            if var_name in self._symbols:\n'
        '                self._instructions.append(\n'
        '                    Instruction("LOAD_VAR", var_name)\n'
        '                )'
    )

    if old_block in content:
        content = content.replace(old_block, new_block)
        with open(path, "w") as f:
            f.write(content)


def main():
    """Diagnose and repair compiler defects, then produce correct output."""
    config = load_config()

    # Diagnosis phase
    has_whitespace_issue = detect_whitespace_in_config(config)
    correct_section, correct_level = find_correct_opt_level(config)
    has_operand_issue = diagnose_constant_fold()
    has_variable_issue = diagnose_variable_resolution()

    # Repair phase - apply fixes based on diagnosis
    if has_whitespace_issue:
        apply_whitespace_fix()

    apply_opt_level_fix(correct_section)

    if has_operand_issue:
        apply_operand_order_fix()

    apply_optimizer_isolation_fix()

    if has_variable_issue:
        apply_variable_resolution_fix()

    # Re-run compiler with all fixes applied
    for key in list(sys.modules.keys()):
        if key.startswith("runtime"):
            del sys.modules[key]
    from runtime.run_compiler import main as run_main
    run_main()


if __name__ == "__main__":
    main()
