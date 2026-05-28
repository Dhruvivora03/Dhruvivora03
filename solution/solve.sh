#!/bin/bash
set -e
python3 /app/runtime/simulate_field.py
python3 /solution/repair_particle_field.py
