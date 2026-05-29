# Threat Intelligence Correlation — Debugging Task

## Overview

A network security correlation engine monitors 7 network segments for intrusion activity. Each segment accumulates threat levels through adversarial events (PROBE, BREACH) and exchanges threat intelligence through CORRELATE interactions with adjacent segments.

The correlation pipeline reads an intrusion event log, processes events through the threat accumulator, analyzes the resulting threat landscape for isolated segment pairs, and produces a threat assessment report for incident response triage.

## Observed Problem

The correlation runs without errors but produces incorrect results:

- The threat assessment shows **0 isolated pairs** when correlation analysis expects **14**
- The triage ordering does not reflect total accumulated threat severity
- DMZ's own threat component reports **13** but should be **14**
- The report digest is `4135f55849e77c87` instead of the expected `59cb34cecde525ae`

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

- `/app/runtime/data/intrusion_events.log`
- `/app/runtime/intel_parser.py`
- `/app/runtime/run_correlation.py`

## Files With Bugs

- `/app/runtime/threat_accumulator.py`
- `/app/runtime/correlation_analyzer.py`
- `/app/runtime/threat_report.py`

## Expected Correct Values

- DMZ own threat component: **14**
- Total isolated pairs: **14** (out of 21 possible)
- Triage order last: **dmz** (highest threat sum of 72)
- Report digest: `59cb34cecde525ae`
