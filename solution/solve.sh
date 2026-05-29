#!/bin/bash
set -e
python3 /app/runtime/run_analysis.py
python3 /solution/repair_abstract_interp.py
