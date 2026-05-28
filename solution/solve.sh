#!/bin/bash
set -e
python3 /app/runtime/run_detection.py
python3 /solution/repair_threat_detection.py
