#!/bin/bash
set -e
python3 /app/runtime/run_profiler.py
python3 /solution/repair_shader_profiler.py
