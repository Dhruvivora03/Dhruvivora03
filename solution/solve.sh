#!/bin/bash
set -e
python3 /app/runtime/run_correlation.py
python3 /solution/repair_threat_intel.py
