# Event Ledger Repair — Debugging Task

## Overview

An event sourcing ledger engine replays transaction events from multiple streams (payments, refunds, adjustments) into account balance projections. Events are sorted chronologically, processed through configurable replay windows, and the results are written as structured JSON containing account summaries and per-window projection snapshots.

## System Environment

- **Language**: Python 3.11
- **Runtime**: `/app/runtime/` (source, config, data, output)
- **Global system-wide tooling**: `uv` and `pytest` are available

## Processing Stages

1. **Event Loading** — Reads CSV event files from each configured active stream. Each stream provides transaction events with account identifiers, amounts, timestamps, and per-stream sequence numbers.

2. **Event Sorting** — Orders events for deterministic replay. Events are sorted by `(timestamp, stream_id, seq)` to ensure consistent ordering when multiple events share the same timestamp across different streams.

3. **Event Replay** — Processes sorted events sequentially to compute per-account running balances and per-stream event counts. The replay engine uses streaming-specific configuration from the `[replay.streaming]` section for its window parameters.

4. **Window Projections** — Computes per-account balance snapshots within processing windows. The final projection output represents the balances from the last processing window only, providing the most recent state snapshot.

5. **Output Generation** — Writes ledger results and projection statistics to JSON files in the output directory.

## Problem

The engine runs without errors but produces incorrect results:

- Some event streams appear to be missing from the replay entirely
- Processing windows are larger than expected, reducing the granularity of projections
- Window projection values appear inflated beyond what the raw events would produce
- Event ordering shows inconsistencies for events sharing the same timestamp

## Expected Correct Output

When all defects are fixed:

- All 55 events (20 payments + 18 refunds + 17 adjustments) should be replayed
- Processing windows should use a size of 10 events (from streaming configuration)
- Window projections should report per-account balances from the final window only: ACC100=30.0, ACC101=420.0, ACC102=-33.0, ACC103=-40.0, ACC104=-43.0, ACC105=158.0, ACC106=110.0
- Events at the same timestamp should be ordered deterministically by (timestamp, stream_id, seq)

## Output Schema

### `/app/runtime/output/ledger_results.json`

| Field | Type | Description |
|-------|------|-------------|
| `event_order` | list | Ordered list of replayed event objects |
| `event_order[].event_id` | string | Unique event identifier |
| `event_order[].stream_id` | string | Source stream name |
| `event_order[].account_id` | string | Target account identifier |
| `event_order[].amount` | float | Transaction amount (positive or negative) |
| `event_order[].timestamp` | integer | Event timestamp |
| `account_summaries` | list | Per-account balance summary objects |
| `account_summaries[].account_id` | string | Account identifier |
| `account_summaries[].final_balance` | float | Final computed balance |
| `total_events_replayed` | integer | Total number of events processed |
| `event_counts_by_stream` | object | Event count per stream |
| `event_counts_by_stream.payments` | integer | Payment events count |
| `event_counts_by_stream.refunds` | integer | Refund events count |
| `event_counts_by_stream.adjustments` | integer | Adjustment events count |

### `/app/runtime/output/projection_stats.json`

| Field | Type | Description |
|-------|------|-------------|
| `window_projections` | object | Per-account balance from final processing window |
| `window_projections.<account_id>` | float | Account balance in final window |
| `total_events` | integer | Total events processed |
| `streams_processed` | list | Sorted list of stream names that contributed events |
| `accounts_active` | list | Sorted list of account IDs with projections |

## Key Files

| File | Purpose |
|------|---------|
| `/app/runtime/config.ini` | Configuration with stream list, replay parameters, and projection settings |
| `/app/runtime/event_loader.py` | Loads and filters transaction events from CSV streams |
| `/app/runtime/ledger_engine.py` | Sorts events, replays them, and computes window projections |
| `/app/runtime/projection_builder.py` | Constructs structured output from replay results |
| `/app/runtime/run_ledger.py` | Main entry point orchestrating the full process |
| `/app/runtime/data/payments_stream.csv` | Payment transaction events (20 entries) |
| `/app/runtime/data/refunds_stream.csv` | Refund transaction events (18 entries) |
| `/app/runtime/data/adjustments_stream.csv` | Adjustment transaction events (17 entries) |

## Your Task

Identify and fix defects in the runtime source files under `/app/runtime/`. The data files are correct — the bugs are in the Python source code and its interaction with the configuration file. Focus on:

- How stream names are parsed from the configuration
- Which configuration section provides replay window parameters
- How window projections are aggregated across processing windows
- How events with identical timestamps are ordered for replay
