#!/bin/bash
set -e
python3 /app/runtime/run_compositor.py
python3 /solution/repair_sdf_compositor.py
