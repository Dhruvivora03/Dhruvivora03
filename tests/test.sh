#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
if [ ! -f /app/runtime/profiler_state.jsonl ]; then
    python3 /app/runtime/run_profiler.py
fi
set +e
uv run --with pytest pytest -v /tests/test_shader_profiler.py
TEST_EXIT=$?
set -e
if [ "$TEST_EXIT" -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; else echo 0 > /logs/verifier/reward.txt; fi
cat /logs/verifier/reward.txt
exit "$TEST_EXIT"
