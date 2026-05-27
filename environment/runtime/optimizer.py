"""Bytecode optimization passes for the compiler.

Implements several standard optimization passes:
  - Constant folding: collapses constant expressions at compile time
  - Dead store elimination: removes stores to variables never loaded
  - Peephole optimization: simplifies instruction sequences

Each pass has a minimum optimization level requirement.
"""

import configparser


class OptimizationPass:
    """Base class for optimization passes."""

    min_level = 1

    def __init__(self, name):
        self.name = name
        self.eliminations = 0

    def apply(self, instructions):
        """Apply the pass and return optimized instruction list."""
        raise NotImplementedError


class ConstantFoldPass(OptimizationPass):
    """Folds constant arithmetic expressions at compile time.

    Detects patterns of PUSH_CONST, PUSH_CONST, OP and replaces
    with a single PUSH_CONST containing the computed result.

    Stack semantics: left operand is deeper on stack (pushed first),
    right operand is on top (pushed second). Binary ops pop both
    and push the result.
    """

    min_level = 1

    def __init__(self):
        super().__init__("constant_fold")
        self._foldable_ops = {"ADD", "SUB", "MUL", "DIV"}

    def apply(self, instructions):
        """Scan for foldable constant pairs and collapse them."""
        from runtime.emitter import Instruction

        result = []
        i = 0
        while i < len(instructions):
            if (i + 2 < len(instructions) and
                    instructions[i].opcode == "PUSH_CONST" and
                    instructions[i + 1].opcode == "PUSH_CONST" and
                    instructions[i + 2].opcode in self._foldable_ops):

                # Fold: compute the result at compile time
                # Stack: first push goes deeper, second push on top
                first_pushed = instructions[i].operand
                second_pushed = instructions[i + 1].operand
                op = instructions[i + 2].opcode

                folded = self._compute(op, second_pushed, first_pushed)
                result.append(Instruction("PUSH_CONST", folded))
                self.eliminations += 2
                i += 3
            else:
                result.append(instructions[i])
                i += 1

        return result

    def _compute(self, op, a, b):
        """Compute binary operation result."""
        if op == "ADD":
            return a + b
        elif op == "SUB":
            return a - b
        elif op == "MUL":
            return a * b
        elif op == "DIV":
            if b == 0:
                return 0
            return a / b
        return 0


class DeadStorePass(OptimizationPass):
    """Eliminates stores to variables that are never subsequently loaded."""

    min_level = 1

    def __init__(self):
        super().__init__("dead_store")

    def apply(self, instructions):
        """Remove STORE_VAR instructions for variables never loaded."""
        from runtime.emitter import Instruction

        # Find all loaded variables
        loaded_vars = set()
        for instr in instructions:
            if instr.opcode == "LOAD_VAR":
                loaded_vars.add(instr.operand)

        # Remove stores to variables never loaded
        result = []
        for instr in instructions:
            if (instr.opcode == "STORE_VAR" and
                    instr.operand not in loaded_vars):
                self.eliminations += 1
                # Also need to remove the preceding value push
                if result and result[-1].opcode in ("PUSH_CONST", "LOAD_VAR"):
                    result.pop()
                    self.eliminations += 1
            else:
                result.append(instr)

        return result


class PeepholePass(OptimizationPass):
    """Peephole optimizer that simplifies local instruction patterns.

    Patterns handled:
      - PUSH_CONST 0, ADD → removed (x + 0 = x)
      - PUSH_CONST 1, MUL → removed (x * 1 = x)
      - PUSH_CONST 0, MUL → replaced with PUSH_CONST 0
    """

    min_level = 2

    def __init__(self):
        super().__init__("peephole")

    def apply(self, instructions):
        """Apply peephole optimization patterns."""
        from runtime.emitter import Instruction

        result = []
        i = 0
        while i < len(instructions):
            if (i + 1 < len(instructions) and
                    instructions[i].opcode == "PUSH_CONST"):
                val = instructions[i].operand
                next_op = instructions[i + 1].opcode

                # x + 0 = x (remove push 0 and ADD)
                if val == 0 and next_op == "ADD":
                    self.eliminations += 2
                    i += 2
                    continue

                # x * 1 = x (remove push 1 and MUL)
                elif val == 1 and next_op == "MUL":
                    self.eliminations += 2
                    i += 2
                    continue

                # x * 0 = 0 (remove everything before, push 0)
                elif val == 0 and next_op == "MUL":
                    if result:
                        result.pop()
                        self.eliminations += 1
                    result.append(Instruction("PUSH_CONST", 0))
                    self.eliminations += 1
                    i += 2
                    continue

            result.append(instructions[i])
            i += 1

        return result


class Optimizer:
    """Orchestrates optimization passes on bytecode."""

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._opt_level = self._config.getint("optimizer", "level")
        self._passes = self._register_passes()

    def _register_passes(self):
        """Register all passes that meet the current optimization level."""
        all_passes = [
            ConstantFoldPass(),
            DeadStorePass(),
            PeepholePass(),
        ]
        # Only include passes whose minimum level is met
        return [p for p in all_passes if p.min_level <= self._opt_level]

    @property
    def active_passes(self):
        return [p.name for p in self._passes]

    @property
    def optimization_level(self):
        return self._opt_level

    def optimize(self, instructions):
        """Run all registered passes on the instruction sequence."""
        current = instructions
        for opt_pass in self._passes:
            current = opt_pass.apply(current)
        return current

    def get_stats(self):
        """Return per-pass elimination statistics."""
        return {p.name: p.eliminations for p in self._passes}

    def total_eliminations(self):
        """Total instructions eliminated across all passes."""
        return sum(p.eliminations for p in self._passes)
