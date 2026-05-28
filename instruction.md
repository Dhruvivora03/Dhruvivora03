# Warzone Campaign State Synchronization -- Debugging Task

## Overview

A multiplayer warzone campaign simulation processes force deployment events across 7 contested zones. The simulation reads a battle trace log of events (PATROL, ASSAULT, RALLY), computes per-zone influence vectors, classifies operational independence between zone pairs, and generates a deployment priority for parallel force scheduling.

The system is producing incorrect results in multiple areas: influence accumulation, independence classification, and deployment priority ordering.

## Expected Behavior

- Each zone maintains a 7-element influence vector tracking accumulated operational strength
- PATROL events add 1 to the zone's own component
- ASSAULT events add 2 to the zone's own component
- RALLY events synchronize influence knowledge with an ally via component-wise maximum AND should record the rally as an active operation
- Operational independence between zones should be determined by the correct mathematical criterion for the influence vector partial order
- Deployment priority should reflect total accumulated influence

## Observed Symptoms

- Zones that have processed RALLY events show influence values that are consistently 1 unit lower than expected in their own component
- The number of independent pairs detected is lower than the true count
- The deployment priority order does not match what total influence sums would produce -- specifically, zones with high peak values in single dimensions are being ranked above zones with higher total influence
- The final state digest does not match the verified correct value

## File Locations

All source files are at `/app/runtime/`:

- `/app/runtime/data/battle_log.txt` -- input trace (CORRECT)
- `/app/runtime/log_reader.py` -- log parser (CORRECT)
- `/app/runtime/run_campaign.py` -- orchestrator (CORRECT)
- `/app/runtime/influence_tracker.py` -- influence vector engine (HAS BUGS)
- `/app/runtime/conflict_resolver.py` -- independence analysis (HAS BUGS)
- `/app/runtime/war_report.py` -- report generation (HAS BUGS -- cascading from analyzer)

## Output Schema

### campaign_state.jsonl (one JSON object per line, sorted by zone_id)
```json
{
  "zone_id": "<zone_name>",
  "influence_vector": [<7 integers>],
  "vector_sum": <integer>,
  "independent_zones": [<list of zone_ids>],
  "priority_rank": <integer 0-6>
}
```

### campaign_summary.json
```json
{
  "digest": "<16-char hex>",
  "total_zones": 7,
  "independent_pair_count": <integer>,
  "independent_pairs": [[<zone_a>, <zone_b>], ...],
  "priority_order": [<zones sorted by priority>],
  "total_influence": <integer>
}
```

## Constraints

- Only standard library modules are used
- Do not modify `log_reader.py`, `run_campaign.py`, or the input data
- The simulation must produce both output files with correct values
- All 14 tests must pass after repair
