#!/bin/bash
set -e
python3 /app/runtime/run_campaign.py
python3 /solution/repair_warzone_sync.py
