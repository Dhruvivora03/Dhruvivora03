#!/bin/bash
# Solution script for token-flow-repair
# Applies fixes to the buggy dataflow analysis modules and re-runs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RUNTIME_DIR="$PROJECT_DIR/runtime"

echo "=== Applying token-flow-repair solution ==="
python "$SCRIPT_DIR/repair_token_flow.py"
echo ""
echo "=== Solution applied successfully ==="
