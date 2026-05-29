#!/bin/bash
set -e
python3 /app/runtime/run_simulation.py
python3 /solution/repair_particle_collision.py
