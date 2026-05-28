"""
Warzone campaign simulation orchestrator.
Coordinates parsing, influence tracking, conflict analysis, and report generation.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from log_reader import parse_battle_log, get_all_zones
from influence_tracker import ZoneTracker
from conflict_resolver import analyze_conflict
from war_report import write_state_file, write_summary_report


def run():
    """Execute the full campaign simulation pipeline."""
    # Step 1: Parse the battle trace log
    events = parse_battle_log()
    all_zones = get_all_zones(events)

    # Step 2: Initialize zone trackers
    zone_trackers = {}
    for zone_id in all_zones:
        zone_trackers[zone_id] = ZoneTracker(zone_id, all_zones)

    # Step 3: Process events through the influence engine
    for event in events:
        zone_id = event["zone_id"]
        tracker = zone_trackers[zone_id]

        if event["event_type"] == "PATROL":
            tracker.apply_patrol()
        elif event["event_type"] == "ASSAULT":
            tracker.apply_assault()
        elif event["event_type"] == "RALLY":
            tracker.apply_rally(event["detail"])

    # Step 4: Collect final vectors
    vectors_dict = {}
    for zone_id in all_zones:
        vectors_dict[zone_id] = zone_trackers[zone_id].get_vector()

    # Step 5: Run conflict analysis
    analysis = analyze_conflict(all_zones, vectors_dict, events)

    # Step 6: Write output files
    records = write_state_file(all_zones, vectors_dict, events, analysis)
    summary = write_summary_report(records, analysis)

    print(f"Campaign complete. Digest: {summary['digest']}")
    print(f"Zones: {summary['total_zones']}, Independent pairs: {summary['independent_pair_count']}")
    print(f"Priority order: {summary['priority_order']}")

    return summary


if __name__ == "__main__":
    run()
