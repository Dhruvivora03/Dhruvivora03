# Network Intrusion Detection Pipeline -- Debugging Task

## Overview

A network intrusion detection system monitors threat propagation across 7 network segments. The pipeline reads a threat event stream (SCAN, EXPLOIT, LATERAL), builds per-segment threat vectors, classifies which segment pairs can be safely isolated for independent incident response, and computes a triage priority for resource allocation.

The system is producing incorrect results in multiple areas: threat level accumulation, isolation classification, and triage ordering.

## Expected Behavior

- Each segment maintains a 7-element threat vector tracking observed threat levels
- SCAN events increment the segment's own threat by 1
- EXPLOIT events increment the segment's own threat by 2
- LATERAL events absorb threat intelligence from adjacent segments (component-wise max) and should always record the propagation as an active event
- Isolation classification should identify all safe isolation pairs
- Triage priority should reflect total accumulated threat

## Observed Symptoms

- Segments that processed LATERAL events show threat values consistently 1 unit lower than expected in their own position
- The number of isolation pairs detected is lower than the true count
- The triage priority order does not match what total threat sums would produce
- The final state fingerprint does not match the verified correct value

## File Locations

All source files are at `/app/runtime/`:

- `/app/runtime/data/threat_events.tsv` -- input event stream (CORRECT)
- `/app/runtime/event_parser.py` -- event parser (CORRECT)
- `/app/runtime/run_detection.py` -- pipeline orchestrator (CORRECT)
- `/app/runtime/propagation_model.py` -- threat propagation engine (HAS BUGS)
- `/app/runtime/segment_classifier.py` -- isolation classification (HAS BUGS)
- `/app/runtime/detection_report.py` -- report generation (HAS BUGS -- cascading from classifier)

## Output Schema

### detection_findings.jsonl (one JSON object per line, sorted by segment_id)
```json
{
  "segment_id": "<segment_name>",
  "threat_vector": [<7 integers>],
  "threat_total": <integer>,
  "isolatable_from": [<list of segment_ids>],
  "triage_rank": <integer 0-6>
}
```

### detection_summary.json
```json
{
  "fingerprint": "<16-char hex>",
  "segment_count": 7,
  "isolation_pair_count": <integer>,
  "isolation_pairs": [[<seg_a>, <seg_b>], ...],
  "triage_order": [<segments sorted by priority>],
  "aggregate_threat": <integer>
}
```

## Constraints

- Only standard library modules are used
- Do not modify `event_parser.py`, `run_detection.py`, or the input data
- The pipeline must produce both output files with correct values
- All 14 tests must pass after repair
