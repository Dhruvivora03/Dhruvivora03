"""Report builder module for the IR optimizer.

Constructs structured output reports from optimization results,
including instruction ordering, pass statistics, and per-module
analysis metrics.
"""


class ReportBuilder:
    """Builds optimization report output."""

    def __init__(self, ordered_instructions, ctx, window_metrics):
        self._ordered = ordered_instructions
        self._ctx = ctx
        self._window_metrics = window_metrics

    def build_optimization_report(self):
        """Build the main optimization report.

        Returns a dict with instruction ordering, elimination stats,
        and module summaries.
        """
        instruction_order = []
        for instr in self._ordered:
            instruction_order.append({
                "instr_id": instr["instr_id"],
                "module_id": instr["module_id"],
                "opcode": instr["opcode"],
                "block_id": instr["block_id"],
                "timestamp": instr["timestamp"],
            })

        module_counts = {}
        for instr in self._ordered:
            mod = instr["module_id"]
            module_counts[mod] = module_counts.get(mod, 0) + 1

        return {
            "instruction_order": instruction_order,
            "total_instructions": len(self._ordered),
            "eliminated_count": self._ctx.eliminated_count,
            "folded_count": self._ctx.folded_count,
            "module_counts": module_counts,
            "pass_depth": None,  # filled by caller
        }

    def build_analysis_report(self):
        """Build the analysis metrics report.

        Returns a dict with per-module window metrics and optimization
        summary statistics.
        """
        return {
            "window_metrics": self._window_metrics,
            "total_instructions": len(self._ordered),
            "modules_analyzed": sorted(
                set(i["module_id"] for i in self._ordered)
            ),
            "optimization_ratio": self._compute_ratio(),
        }

    def _compute_ratio(self):
        """Compute overall optimization ratio."""
        total = len(self._ordered)
        if total == 0:
            return 0.0
        optimized = self._ctx.eliminated_count + self._ctx.folded_count
        return round(optimized / total, 4)
