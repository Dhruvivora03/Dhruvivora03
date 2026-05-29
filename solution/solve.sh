#!/bin/bash
set -e
python3 /app/runtime/run_bci.py
python3 /solution/repair_eeg_coherence.py
