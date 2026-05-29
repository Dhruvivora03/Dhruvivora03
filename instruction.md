# Threat Intelligence Correlation — Debugging Task

## Overview

A network security correlation engine monitors 7 network segments for intrusion activity. Each segment accumulates threat levels through adversarial events (PROBE, BREACH) and exchanges threat intelligence through CORRELATE interactions with adjacent segments.

The correlation pipeline reads an intrusion event log, processes events through the threat accumulator, analyzes the resulting threat landscape for isolated segment pairs, and produces a threat assessment report for incident response triage.

## Observed Problem

The correlation runs without errors but produces incorrect results:

- The threat assessment shows **0 isolated pairs** when correlation analysis expects **18**
- The triage ordering does not reflect total accumulated threat severity
- DMZ's own threat component reports **14** but integration of its event history (4 PROBE + 2 BREACH + 2 CORRELATE) should yield **15**
- The report digest is `73f11ba9384eda64` instead of the expected `4f6097112936e335`

## File Layout

```
/app/runtime/
├── data/
│   └── intrusion_events.log   # Event trace (correct, do not modify)
├── intel_parser.py            # Log parser (correct, do not modify)
├── threat_accumulator.py      # Threat vector engine (contains bug)
├── correlation_analyzer.py    # Correlation analysis (contains bugs)
├── threat_report.py           # Report generation (affected by analyzer bugs)
└── run_correlation.py         # Orchestrator (correct, do not modify)
```

## Correct Files (do not modify)

- `/app/runtime/data/intrusion_events.log` — the raw event trace
- `/app/runtime/intel_parser.py` — parses the pipe-separated log format
- `/app/runtime/run_correlation.py` — orchestrates parsing, accumulation, and reporting

## Files With Bugs

- `/app/runtime/threat_accumulator.py` — threat vector computation
- `/app/runtime/correlation_analyzer.py` — isolation analysis and triage ordering
- `/app/runtime/threat_report.py` — report generation (imports from correlation_analyzer)

## Output Schema

### segment_state.jsonl
```json
{"segment_id": "dmz", "threat_vector": [10, 10, 15, 10, 9, 9, 10], "vector_sum": 73}
```

### threat_assessment.jsonl
```json
{"type": "segment_state", "segment_id": "dmz", "threat_vector": [...], "vector_sum": 73}
{"type": "correlation_analysis", "isolated_pairs": [...], "isolated_count": 18, "triage_order": [...]}
{"type": "digest", "fingerprint": "4f6097112936e335"}
```

## Expected Correct Values

- DMZ own threat component: **15**
- Total isolated pairs: **18** (out of 21 possible)
- Triage order last: **dmz** (highest threat sum of 73)
- Report digest: `4f6097112936e335`
