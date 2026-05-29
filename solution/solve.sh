#!/bin/bash
set -e
python3 /app/runtime/run_forensics.py
python3 /solution/repair_audio_forensics.py
