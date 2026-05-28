#!/bin/bash
# Test runner for token-flow-repair task
# Runs the analysis and then validates with pytest

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RUNTIME_DIR="$PROJECT_DIR/runtime"

# Run the analysis first
echo "=== Running dataflow analysis ==="
cd "$RUNTIME_DIR"
python run_analysis.py

# Run tests
echo ""
echo "=== Running test suite ==="
cd "$PROJECT_DIR"
python -m pytest tests/test_dataflow.py -v --tb=short 2>&1

echo ""
echo "=== Test run complete ==="
