"""
War campaign report writer.
Generates the final JSONL state file and summary report combining
zone influence state with conflict analysis results.
"""

import json
import hashlib
import os

from conflict_resolver import zones_are_operationally_independent

OUTPUT_DIR = os.path.dirname(__file__)
STATE_FILE = os.path.join(OUTPUT_DIR, "campaign_state.jsonl")
REPORT_FILE = os.path.join(OUTPUT_DIR, "campaign_summary.json")


def write_state_file(zones, vectors_dict, events, analysis):
    """Write per-zone state records to JSONL file."""
    records = []
    sorted_zones = sorted(zones)

    for zone in sorted_zones:
        vec = vectors_dict[zone]
        # Determine which other zones this zone is operationally independent from
        independent_with = []
        for other in sorted_zones:
            if other == zone:
                continue
            if zones_are_operationally_independent(vec, vectors_dict[other]):
                independent_with.append(other)

        record = {
            "zone_id": zone,
            "influence_vector": vec,
            "vector_sum": sum(vec),
            "independent_zones": independent_with,
            "priority_rank": analysis["priority_order"].index(zone),
        }
        records.append(record)

    with open(STATE_FILE, "w") as f:
        for rec in records:
            f.write(json.dumps(rec, sort_keys=True) + "\n")

    return records


def compute_digest(records):
    """Compute a 16-character hex digest of the full state."""
    content = json.dumps(records, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()[:16]


def write_summary_report(records, analysis):
    """Write the summary report with digest and statistics."""
    digest = compute_digest(records)

    summary = {
        "digest": digest,
        "total_zones": len(records),
        "independent_pair_count": len(analysis["independent_pairs"]),
        "independent_pairs": [list(p) for p in analysis["independent_pairs"]],
        "priority_order": analysis["priority_order"],
        "total_influence": sum(r["vector_sum"] for r in records),
    }

    with open(REPORT_FILE, "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    return summary
