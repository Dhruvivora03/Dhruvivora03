"""Optimization pass engine for the IR optimizer.

Applies optimization passes (constant folding, dead code elimination)
to IR instruction streams. Instructions are ordered for processing
and analyzed in configurable windows for resource tracking.
"""

import configparser


class OptimizationContext:
    """Tracks state across optimization passes."""

    def __init__(self, instructions):
        self._instructions = instructions
        self._eliminated = set()
        self._folded = set()
        self._constants = {}

    @property
    def live_instructions(self):
        return [i for i in self._instructions
                if i["instr_id"] not in self._eliminated]

    @property
    def eliminated_count(self):
        return len(self._eliminated)

    @property
    def folded_count(self):
        return len(self._folded)

    def mark_eliminated(self, instr_id):
        self._eliminated.add(instr_id)

    def mark_folded(self, instr_id):
        self._folded.add(instr_id)

    def set_constant(self, dest, value):
        self._constants[dest] = value

    def get_constant(self, reg):
        return self._constants.get(reg)

    def is_constant(self, reg):
        return reg in self._constants or (
            reg and reg.startswith("const_")
        )


class PassEngine:
    """Executes optimization passes on IR instruction streams."""

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._pass_depth = self._config.getint("optimizer", "pass_depth")
        self._inline_threshold = self._config.getint(
            "optimizer", "inline_threshold"
        )
        self._window_size = self._config.getint("analysis", "window_size")

    @property
    def pass_depth(self):
        return self._pass_depth

    @property
    def inline_threshold(self):
        return self._inline_threshold

    @property
    def window_size(self):
        return self._window_size

    def order_instructions(self, instructions):
        """Order instructions for optimization pass processing.

        Instructions are ordered by timestamp for sequential processing.
        For instructions with identical timestamps, ordering uses seq
        to break ties deterministically.
        """
        # Note: seq is local to each module
        return sorted(
            instructions,
            key=lambda i: (i["timestamp"], i["seq"])
        )

    def run_passes(self, ordered_instructions):
        """Run optimization passes over ordered instructions.

        Applies constant folding and dead code elimination for
        the configured number of pass iterations.
        """
        ctx = OptimizationContext(ordered_instructions)

        for pass_num in range(self._pass_depth):
            self._run_single_pass(ctx, pass_num)

        return ctx

    def _run_single_pass(self, ctx, pass_num):
        """Execute a single optimization pass."""
        for instr in ctx.live_instructions:
            # Constant folding: if both sources are constants
            if self._can_fold(ctx, instr):
                ctx.mark_folded(instr["instr_id"])
                if instr["dest"]:
                    ctx.set_constant(instr["dest"], f"folded_{pass_num}")

            # Dead code elimination: instructions with unused results
            # beyond the inline threshold are candidates
            if instr["dest"] and instr["opcode"] not in (
                "store", "br_cond", "br_uncond"
            ):
                uses = self._count_uses(ctx, instr["dest"])
                if uses == 0 and instr["seq"] > self._inline_threshold:
                    ctx.mark_eliminated(instr["instr_id"])

    def _can_fold(self, ctx, instr):
        """Check if an instruction can be constant-folded."""
        if instr["opcode"] in ("br_cond", "br_uncond", "phi",
                                "load", "store"):
            return False
        if not instr["src1"]:
            return False
        src1_const = ctx.is_constant(instr["src1"])
        src2_const = ctx.is_constant(instr["src2"]) if instr["src2"] else True
        return src1_const and src2_const

    def _count_uses(self, ctx, dest):
        """Count how many live instructions use a register."""
        count = 0
        for instr in ctx.live_instructions:
            if instr["src1"] == dest or instr["src2"] == dest:
                count += 1
        return count

    def compute_window_metrics(self, ordered_instructions, ctx):
        """Compute per-window optimization metrics.

        Processes instructions in analysis windows of configured size.
        The final metrics should reflect counts from the last window
        only, representing the most recent analysis state.
        """
        module_metrics = {}

        for i in range(0, len(ordered_instructions), self._window_size):
            window = ordered_instructions[i:i + self._window_size]
            window_counts = {}

            for instr in window:
                mod = instr["module_id"]
                if mod not in window_counts:
                    window_counts[mod] = {"total": 0, "optimized": 0}
                window_counts[mod]["total"] += 1
                if (instr["instr_id"] in ctx._eliminated or
                        instr["instr_id"] in ctx._folded):
                    window_counts[mod]["optimized"] += 1

            # Accumulate across windows
            for mod, counts in window_counts.items():
                if mod not in module_metrics:
                    module_metrics[mod] = {"total": 0, "optimized": 0}
                module_metrics[mod]["total"] += counts["total"]
                module_metrics[mod]["optimized"] += counts["optimized"]

        return module_metrics
