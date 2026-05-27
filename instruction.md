# Event Store Replay Repair — Debugging Task

## Overview

An event sourcing engine ingests domain events from multiple stream sources (orders, payments, inventory), stores them in an append-only event store, replays them in deterministic global order, and builds materialized view projections with aggregate statistics. The system processes streams in configurable replay windows and produces JSON output containing projection results and store statistics.

## System Environment

- **Language**: Python 3.11
- **Runtime**: `/app/runtime/` (source, config, data, output)
- **Global system-wide tooling**: `uv` and `pytest` are available

## Processing Stages

1. **Stream Loading** — Reads CSV stream files (orders, payments, inventory) based on the active streams configuration. Each stream provides domain events with timestamps, sequence numbers, and payload data.

2. **Event Store Population** — Appends loaded events to an append-only store. Snapshots are created at configurable intervals using parameters from the `[projection.incremental]` configuration section for incremental processing support.

3. **Replay Ordering** — Produces a deterministic global event sequence from all streams. Events are sorted by `(timestamp, stream_id, sequence_number)` to ensure consistent ordering when multiple streams contain events at the same timestamp.

4. **Projection Building** — Builds materialized views by replaying ordered events. Groups events by entity and computes running totals for amounts and event counts.

5. **Window Aggregates** — Processes replay events in configurable window sizes and computes per-stream event counts. The final aggregates represent the counts from the last processing window only.

6. **Output Generation** — Writes projection results and store statistics to JSON files in the output directory.

## Problem

The engine runs without errors but produces incorrect results:

- Some stream events appear to be missing from the store entirely
- The snapshot mechanism never triggers despite sufficient events being stored
- Window aggregates report inflated counts that exceed actual per-window event numbers
- The replay sequence shows non-deterministic ordering for events at the same timestamp

## Expected Correct Output

When all defects are fixed:

- All 56 events (22 orders + 18 payments + 16 inventory) should be stored
- The event store should use a snapshot interval of 10, creating 5 snapshots (at events 10, 20, 30, 40, 50)
- Window aggregates should report per-stream counts from the final window only (window_size=20, last window has 16 events): orders=4, payments=5, inventory=7
- The replay sequence should be deterministically ordered by (timestamp, stream_id, sequence_number)

## Output Schema

### `/app/runtime/output/projection_results.json`

| Field | Type | Description |
|-------|------|-------------|
| `replay_sequence` | list | Ordered list of replayed event objects |
| `replay_sequence[].event_id` | string | Unique event identifier |
| `replay_sequence[].stream_id` | string | Source stream name |
| `replay_sequence[].event_type` | string | Type of domain event |
| `replay_sequence[].timestamp` | integer | Event timestamp |
| `replay_sequence[].sequence_number` | integer | Per-stream sequence number |
| `replay_sequence[].payload_amount` | float | Event payload amount |
| `projections` | list | List of entity projection objects |
| `projections[].entity_id` | string | Entity identifier |
| `projections[].stream_id` | string | Primary stream for entity |
| `projections[].event_count` | integer | Total events for entity |
| `projections[].total_amount` | float | Sum of payload amounts |
| `projections[].last_event_type` | string | Most recent event type |
| `projections[].last_timestamp` | integer | Most recent event timestamp |
| `total_events_replayed` | integer | Total number of events in store |

### `/app/runtime/output/store_stats.json`

| Field | Type | Description |
|-------|------|-------------|
| `total_events` | integer | Total events in the store |
| `snapshot_interval` | integer | Configured snapshot interval |
| `snapshots_created` | integer | Number of snapshots taken |
| `stream_counts` | object | Per-stream event counts |
| `stream_counts.orders` | integer | Orders stream event count |
| `stream_counts.payments` | integer | Payments stream event count |
| `stream_counts.inventory` | integer | Inventory stream event count |
| `window_aggregates` | object | Per-stream counts from final replay window |
| `window_aggregates.orders` | integer | Orders events in final window |
| `window_aggregates.payments` | integer | Payments events in final window |
| `window_aggregates.inventory` | integer | Inventory events in final window |
| `replay_checksum` | string | MD5 checksum of replay event ID sequence |

## Key Files

| File | Purpose |
|------|---------|
| `/app/runtime/config.ini` | Configuration with stream list, projection parameters, and replay settings |
| `/app/runtime/stream_loader.py` | Loads and filters domain events from CSV streams |
| `/app/runtime/event_store.py` | Append-only event store with snapshot support and replay ordering |
| `/app/runtime/projection_engine.py` | Builds projections in replay windows and computes aggregates |
| `/app/runtime/run_replay.py` | Main entry point orchestrating the full process |
| `/app/runtime/data/orders_stream.csv` | Order domain events (22 entries) |
| `/app/runtime/data/payments_stream.csv` | Payment domain events (18 entries) |
| `/app/runtime/data/inventory_stream.csv` | Inventory domain events (16 entries) |

## Your Task

Identify and fix defects in the runtime source files under `/app/runtime/`. The data files are correct — the bugs are in the Python source code and its interaction with the configuration file. Focus on:

- How stream names are parsed from the configuration
- Which configuration section provides snapshot interval parameters
- How window aggregates are computed across replay windows
- How replay ordering handles timestamp ties between different streams
