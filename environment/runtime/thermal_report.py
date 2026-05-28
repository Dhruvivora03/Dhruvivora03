"""
Thermal simulation report writer.
Generates the final JSONL state file and summary report combining
engine state with lattice analysis results.
"""

import json
import hashlib
import os

from lattice_analyzer import nodes_are_thermally_independent

OUTPUT_DIR = os.path.dirname(__file__)
STATE_FILE = os.path.join(OUTPUT_DIR, "thermal_state.jsonl")
REPORT_FILE = os.path.join(OUTPUT_DIR, "thermal_summary.json")


def write_state_file(nodes, vectors_dict, events, analysis):
    """Write per-node state records to JSONL file."""
    records = []
    sorted_nodes = sorted(nodes)

    for node in sorted_nodes:
        vec = vectors_dict[node]
        # Determine which other nodes this node is thermally independent from
        independent_with = []
        for other in sorted_nodes:
            if other == node:
                continue
            if nodes_are_thermally_independent(vec, vectors_dict[other]):
                independent_with.append(other)

        record = {
            "node_id": node,
            "energy_vector": vec,
            "vector_sum": sum(vec),
            "independent_neighbors": independent_with,
            "priority_rank": analysis["priority_order"].index(node),
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
        "total_nodes": len(records),
        "independent_pair_count": len(analysis["independent_pairs"]),
        "independent_pairs": [list(p) for p in analysis["independent_pairs"]],
        "priority_order": analysis["priority_order"],
        "total_energy": sum(r["vector_sum"] for r in records),
    }

    with open(REPORT_FILE, "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    return summary
