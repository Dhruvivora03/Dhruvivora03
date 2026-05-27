"""Main compiler module that orchestrates parsing, emission, and optimization.

Processes source files from the configured input directory, compiles
each to bytecode, optimizes, and collects statistics for batch output.
"""

import configparser
import os

from runtime.parser import Parser
from runtime.emitter import BytecodeEmitter
from runtime.optimizer import Optimizer


class CompilationUnit:
    """Represents a single compiled source file."""

    def __init__(self, filename, statements, raw_bytecode, opt_bytecode,
                 symbols, stats):
        self.filename = filename
        self.statements = statements
        self.raw_bytecode = raw_bytecode
        self.optimized_bytecode = opt_bytecode
        self.symbols = symbols
        self.stats = stats

    @property
    def raw_count(self):
        return len(self.raw_bytecode)

    @property
    def optimized_count(self):
        return len(self.optimized_bytecode)


class BatchCompiler:
    """Compiles multiple source files and produces aggregate statistics."""

    def __init__(self, config_path):
        self._config = configparser.ConfigParser()
        self._config.read(config_path)
        self._source_dir = os.path.join(
            os.path.dirname(config_path),
            self._config.get("compiler", "source_dir")
        )
        raw_sources = self._config.get("compiler", "source_files")
        self._source_files = set(raw_sources.split(","))
        self._optimizer = Optimizer(config_path)
        self._units = []

    @property
    def units(self):
        return list(self._units)

    def compile_all(self):
        """Compile all configured source files."""
        self._units = []
        for filename in sorted(self._source_files):
            filepath = os.path.join(self._source_dir, filename)
            if not os.path.exists(filepath):
                continue
            unit = self._compile_file(filepath, filename)
            self._units.append(unit)
        return self._units

    def _compile_file(self, filepath, filename):
        """Compile a single source file to optimized bytecode."""
        with open(filepath, "r") as f:
            source = f.read()

        # Parse
        parser = Parser()
        statements = parser.parse(source)
        symbols = parser.symbol_table

        # Emit bytecode
        emitter = BytecodeEmitter(symbols)
        raw_bytecode = emitter.emit_program(statements)

        # Optimize
        opt_bytecode = self._optimizer.optimize(list(raw_bytecode))

        stats = self._optimizer.get_stats()

        return CompilationUnit(
            filename=filename,
            statements=statements,
            raw_bytecode=raw_bytecode,
            opt_bytecode=opt_bytecode,
            symbols=symbols,
            stats=stats,
        )

    def aggregate_stats(self):
        """Compute aggregate compilation statistics across all units.

        Returns per-file instruction counts and pass-level elimination data.
        """
        file_stats = []
        total_eliminated = 0

        for unit in self._units:
            eliminated = unit.raw_count - unit.optimized_count
            total_eliminated += eliminated
            file_stats.append({
                "filename": unit.filename,
                "raw_instructions": unit.raw_count,
                "optimized_instructions": unit.optimized_count,
                "eliminated": eliminated,
                "pass_stats": unit.stats,
            })

        return {
            "files_compiled": len(self._units),
            "file_stats": file_stats,
            "total_instructions_eliminated": total_eliminated,
            "pass_eliminations": self._optimizer.get_stats(),
            "optimization_level": self._optimizer.optimization_level,
            "active_passes": self._optimizer.active_passes,
        }
